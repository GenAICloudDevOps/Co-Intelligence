from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from auth.utils import get_current_user
from auth.models import User
from .models import Topic, TutorSession, Assessment, Progress, ChatMessage
from .graph import create_tutor_graph
import json

router = APIRouter()
tutor_graph = create_tutor_graph()

class ChatRequest(BaseModel):
    session_id: int | None = None
    topic_id: int
    message: str
    model: str = "gemini-2.5-flash-lite"

class SessionCreate(BaseModel):
    topic_id: int

@router.get("/topics")
async def get_topics():
    """Get all available topics"""
    topics = await Topic.all()
    return [{"id": t.id, "name": t.name, "category": t.category, "difficulty": t.difficulty, "description": t.description} for t in topics]

@router.post("/sessions")
async def create_session(data: SessionCreate, current_user: User = Depends(get_current_user)):
    """Start a new learning session"""
    topic = await Topic.get(id=data.topic_id)
    session = await TutorSession.create(user_id=current_user.id, topic_id=topic.id)
    return {"id": session.id, "topic": topic.name, "status": session.status}

@router.get("/sessions")
async def get_sessions(current_user: User = Depends(get_current_user)):
    """Get user's sessions"""
    sessions = await TutorSession.filter(user_id=current_user.id).prefetch_related('topic').order_by('-created_at')
    return [{"id": s.id, "topic": s.topic.name, "status": s.status, "created_at": s.created_at} for s in sessions]

@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: int, current_user: User = Depends(get_current_user)):
    """Get chat history"""
    session = await TutorSession.get_or_none(id=session_id, user_id=current_user.id)
    if not session:
        return []
    
    messages = await ChatMessage.filter(session_id=session_id).order_by('created_at')
    return [{"role": m.role, "content": m.content, "agent_type": m.agent_type} for m in messages]

@router.post("/chat")
async def chat(data: ChatRequest, current_user: User = Depends(get_current_user)):
    """Chat with tutor"""
    # Get or create session
    if data.session_id:
        session = await TutorSession.get(id=data.session_id, user_id=current_user.id)
    else:
        topic = await Topic.get(id=data.topic_id)
        session = await TutorSession.create(user_id=current_user.id, topic_id=topic.id)
    
    topic = await session.topic
    
    # Get conversation history
    messages = await ChatMessage.filter(session_id=session.id).order_by('created_at')
    history = [{"role": m.role, "content": m.content} for m in messages[-6:]]
    
    # Save user message
    await ChatMessage.create(session_id=session.id, role='user', content=data.message)
    
    # Check if in assessment mode
    last_message = messages[-1] if messages else None
    assessment_mode = last_message and last_message.agent_type == 'assessor'
    
    # Run through LangGraph
    state = {
        'user_id': current_user.id,
        'session_id': session.id,
        'topic': topic.name,
        'difficulty': session.current_difficulty,
        'user_message': data.message,
        'conversation_history': history,
        'intent': '',
        'response': '',
        'current_question': {},
        'assessment_mode': assessment_mode,
        'model': data.model
    }
    
    result = tutor_graph.invoke(state)
    
    # Save assistant response
    agent_type = result.get('intent', 'teach')
    await ChatMessage.create(
        session_id=session.id,
        role='assistant',
        content=result['response'],
        agent_type=agent_type
    )
    
    return {
        "session_id": session.id,
        "response": result['response'],
        "agent_type": agent_type,
        "assessment_mode": result.get('assessment_mode', False)
    }

@router.get("/progress")
async def get_progress(current_user: User = Depends(get_current_user)):
    """Get user's learning progress"""
    progress = await Progress.filter(user_id=current_user.id).prefetch_related('topic')
    return [{
        "topic": p.topic.name,
        "assessments_taken": p.assessments_taken,
        "average_score": p.average_score,
        "completed": p.completed
    } for p in progress]
