"""Routes for AI Agent app."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.utils import get_current_user
from auth.models import User

from .agent import run_agent
from .executor import cleanup_executor

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    history: list[dict] | None = None


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
        )
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            served_url=result.get("served_url"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/cleanup")
async def cleanup_session(session_id: str, user: User = Depends(get_current_user)):
    """Cleanup a session's container."""
    if not session_id.startswith(f"{user.id}-"):
        raise HTTPException(status_code=403, detail="Not your session")
    await cleanup_executor(session_id)
    return {"status": "cleaned up"}
