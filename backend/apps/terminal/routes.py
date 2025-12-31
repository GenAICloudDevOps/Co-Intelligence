import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from auth.models import User
from config import settings

from .session_manager import create_session, close_session

router = APIRouter()


async def _get_current_user_ws(websocket: WebSocket) -> User | None:
    token = None
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        token = websocket.cookies.get(settings.COOKIE_ACCESS_NAME)
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        return None

    return await User.get_or_none(id=user_id)


@router.websocket("/ws")
async def terminal_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    user = await _get_current_user_ws(websocket)
    if not user:
        await websocket.close(code=1008)
        return

    try:
        cols = int(websocket.query_params.get("cols", 80))
        rows = int(websocket.query_params.get("rows", 24))
    except ValueError:
        cols, rows = 80, 24

    session = None
    output_task = None
    try:
        session = await create_session(user.id, cols=cols, rows=rows)

        async def _send_output(data: bytes) -> None:
            if websocket.client_state.name != "CONNECTED":
                return
            text = data.decode("utf-8", errors="ignore")
            await websocket.send_text(json.dumps({"type": "output", "data": text}))

        output_task = asyncio.create_task(session.stream_output(_send_output))
        await websocket.send_text(json.dumps({"type": "ready", "sessionId": session.id}))

        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = payload.get("type")
            if msg_type == "input":
                session.write(payload.get("data", ""))
            elif msg_type == "resize":
                try:
                    cols = int(payload.get("cols", session.cols))
                    rows = int(payload.get("rows", session.rows))
                    session.resize(cols, rows)
                except (TypeError, ValueError):
                    continue
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
    finally:
        if output_task:
            output_task.cancel()
        if session:
            await close_session(session.id)
