from tortoise import fields
from tortoise.models import Model

class ChatSession(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    title = fields.CharField(max_length=255, default="New Chat")
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "chat_sessions"

class ChatMessage(Model):
    id = fields.IntField(pk=True)
    session_id = fields.IntField()
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    model = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "chat_messages"

class ChatDocument(Model):
    id = fields.IntField(pk=True)
    session_id = fields.IntField()
    filename = fields.CharField(max_length=255)
    file_size = fields.IntField()
    file_type = fields.CharField(max_length=50)
    s3_url = fields.CharField(max_length=500, null=True)
    extracted_text = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "chat_documents"
