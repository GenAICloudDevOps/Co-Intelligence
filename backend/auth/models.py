from tortoise import fields
from models.base import BaseModel

class User(BaseModel):
    email = fields.CharField(max_length=255, unique=True)
    username = fields.CharField(max_length=100, unique=True)
    hashed_password = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    role = fields.CharField(max_length=50, default="user")
    
    class Meta:
        table = "users"
