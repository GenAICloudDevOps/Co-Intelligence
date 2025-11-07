from tortoise import fields
from models.base import BaseModel

class ChatSession(BaseModel):
    user_id = fields.IntField()
    title = fields.CharField(max_length=255, default="New Chat")
    
    class Meta:
        table = "chat_sessions"

class ChatMessage(BaseModel):
    session_id = fields.IntField()
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    model = fields.CharField(max_length=100, null=True)
    
    class Meta:
        table = "chat_messages"

class ChatDocument(BaseModel):
    session_id = fields.IntField()
    filename = fields.CharField(max_length=255)
    file_size = fields.IntField()
    file_type = fields.CharField(max_length=50)
    s3_url = fields.CharField(max_length=500, null=True)
    extracted_text = fields.TextField()
    
    class Meta:
        table = "chat_documents"
