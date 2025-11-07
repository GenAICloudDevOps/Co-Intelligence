from tortoise import fields
from .base import BaseModel

class AppRole(BaseModel):
    """App-specific roles for users"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="app_roles")
    app_name = fields.CharField(max_length=50)  # "insurance-claims", "ai-chat", etc.
    role = fields.CharField(max_length=50)  # "customer", "agent", "adjuster", "manager", "admin"
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "app_roles"
        unique_together = (("user_id", "app_name", "role"),)
