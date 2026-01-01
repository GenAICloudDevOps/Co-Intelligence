"""Routes for AI Agent app."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from auth.utils import get_current_user
from auth.models import User

from .agent import run_agent
from .executor import cleanup_executor, get_local_workspace

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    history: list[dict] | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    served_url: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    """Chat with the AI agent."""
    session_id = request.session_id or f"{user.id}-{uuid.uuid4().hex[:8]}"

    try:
        result = await run_agent(
            session_id=session_id,
            user_message=request.message,
            history=request.history,
            model_name=request.model,
        )
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            served_url=result.get("served_url"),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/sessions/{session_id}/cleanup")
async def cleanup_session(session_id: str, user: User = Depends(get_current_user)):
    """Cleanup a session's container."""
    if not session_id.startswith(f"{user.id}-"):
        raise HTTPException(status_code=403, detail="Not your session")
    await cleanup_executor(session_id)
    return {"status": "cleaned up"}


@router.get("/sessions/{session_id}/files/{file_path:path}")
async def serve_file(session_id: str, file_path: str, user: User = Depends(get_current_user)):
    """Serve locally stored AI agent files when Docker isn't available."""
    if not session_id.startswith(f"{user.id}-"):
        raise HTTPException(status_code=403, detail="Not your session")
    base = get_local_workspace(session_id).resolve()
    target = (base / file_path).resolve()
    if target != base and base not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)
