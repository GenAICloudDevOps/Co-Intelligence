from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from auth.utils import get_current_user
from auth.models import User
from apps.ai_chat.models import ChatSession, ChatMessage, ChatDocument
from apps.ai_chat.agent import stream_model
from apps.ai_chat.utils import extract_text_from_file, upload_to_s3
import json

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str
    model: str = "gemini"
    context_size: int = 10
    web_search: bool = False

class SessionCreate(BaseModel):
    title: str = "New Chat"

@router.post("/sessions")
async def create_session(data: SessionCreate, current_user: User = Depends(get_current_user)):
    session = await ChatSession.create(user_id=current_user.id, title=data.title)
    return {"id": session.id, "title": session.title, "created_at": session.created_at}

@router.get("/sessions")
async def get_sessions(current_user: User = Depends(get_current_user)):
    sessions = await ChatSession.filter(user_id=current_user.id).order_by("-created_at")
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]

@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: int, current_user: User = Depends(get_current_user)):
    session = await ChatSession.get_or_none(id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = await ChatMessage.filter(session_id=session_id).order_by("created_at")
    return [{"role": m.role, "content": m.content, "model": m.model, "created_at": m.created_at} for m in messages]

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, current_user: User = Depends(get_current_user)):
    session = await ChatSession.get_or_none(id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await ChatMessage.filter(session_id=session_id).delete()
    await ChatDocument.filter(session_id=session_id).delete()
    await session.delete()
    return {"message": "Session deleted"}

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    session_id: int = Form(...),
    current_user: User = Depends(get_current_user)
):
    session = await ChatSession.get_or_none(id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    file_content = await file.read()
    file_size = len(file_content)
    
    try:
        extracted_text = extract_text_from_file(file.filename, file_content)
        s3_url = upload_to_s3(file_content, file.filename, session_id)
        
        document = await ChatDocument.create(
            session_id=session_id,
            filename=file.filename,
            file_size=file_size,
            file_type=file.content_type or "application/octet-stream",
            s3_url=s3_url,
            extracted_text=extracted_text[:50000]  # Limit to 50k chars
        )
        
        return {
            "id": document.id,
            "filename": document.filename,
            "file_size": document.file_size,
            "file_type": document.file_type,
            "text_length": len(extracted_text)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

@router.get("/sessions/{session_id}/documents")
async def get_documents(session_id: int, current_user: User = Depends(get_current_user)):
    session = await ChatSession.get_or_none(id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    documents = await ChatDocument.filter(session_id=session_id).order_by("-created_at")
    return [{
        "id": d.id,
        "filename": d.filename,
        "file_size": d.file_size,
        "file_type": d.file_type,
        "created_at": d.created_at
    } for d in documents]

@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, current_user: User = Depends(get_current_user)):
    document = await ChatDocument.get_or_none(id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    session = await ChatSession.get_or_none(id=document.session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    await document.delete()
    return {"message": "Document deleted"}

@router.post("/chat")
async def chat(data: ChatRequest, current_user: User = Depends(get_current_user)):
    if not data.session_id:
        session = await ChatSession.create(user_id=current_user.id)
        session_id = session.id
    else:
        session = await ChatSession.get_or_none(id=data.session_id, user_id=current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = data.session_id
    
    await ChatMessage.create(session_id=session_id, role="user", content=data.message)
    
    # Non-streaming endpoint - deprecated, use /chat/stream instead
    # result = await chat_graph.ainvoke({
    #     "messages": [{"role": "user", "content": data.message}],
    #     "model": data.model
    # })
    # response_text = result["response"]
    
    response_text = "Please use /chat/stream endpoint for responses"
    await ChatMessage.create(session_id=session_id, role="assistant", content=response_text, model=data.model)
    
    return {"session_id": session_id, "response": response_text}

@router.post("/chat/stream")
async def chat_stream(data: ChatRequest, current_user: User = Depends(get_current_user)):
    if not data.session_id:
        session = await ChatSession.create(user_id=current_user.id)
        session_id = session.id
    else:
        session = await ChatSession.get_or_none(id=data.session_id, user_id=current_user.id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = data.session_id
    
    await ChatMessage.create(session_id=session_id, role="user", content=data.message)
    
    # Get context messages
    all_messages = await ChatMessage.filter(session_id=session_id).order_by("-created_at").limit(data.context_size * 2)
    context_messages = [{"role": m.role, "content": m.content} for m in reversed(list(all_messages))]
    
    # Get document context
    documents = await ChatDocument.filter(session_id=session_id).all()
    document_context = ""
    if documents:
        document_context = "\n\n---\n\n".join([
            f"Document: {d.filename}\n{d.extracted_text[:5000]}"  # First 5k chars per doc
            for d in documents
        ])
    
    async def generate():
        full_response = ""
        async for chunk in stream_model(
            [{"role": "user", "content": data.message}],
            data.model,
            context_messages[:-1],  # Exclude the user message we just added
            document_context,
            data.web_search
        ):
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk, 'session_id': session_id})}\n\n"
        
        # Save complete response
        await ChatMessage.create(session_id=session_id, role="assistant", content=full_response, model=data.model)
        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/sessions/{session_id}/context")
async def get_context_info(session_id: int, context_size: int = 10, current_user: User = Depends(get_current_user)):
    session = await ChatSession.get_or_none(id=session_id, user_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    total_messages = await ChatMessage.filter(session_id=session_id).count()
    context_messages = min(total_messages, context_size * 2)
    
    return {
        "total_messages": total_messages,
        "context_messages": context_messages,
        "context_size": context_size
    }
