from tortoise import fields
from models.base import BaseModel

class User(BaseModel):
    email = fields.CharField(max_length=255, unique=True)
    username = fields.CharField(max_length=100, unique=True)
    hashed_password = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    global_role = fields.CharField(max_length=50, default="user")  # Platform-wide role: user, agent, adjuster, manager, admin
    email_notifications_enabled = fields.BooleanField(default=False)
    
    class Meta:
        table = "users"

class RefreshToken(BaseModel):
    user_id = fields.IntField()
    token = fields.CharField(max_length=255, unique=True)
    expires_at = fields.DatetimeField()
    
    class Meta:
        table = "refresh_tokens"

class PasswordResetToken(BaseModel):
    user_id = fields.IntField()
    token = fields.CharField(max_length=255, unique=True)
    expires_at = fields.DatetimeField()
    used_at = fields.DatetimeField(null=True)

    class Meta:
        table = "password_reset_tokens"
