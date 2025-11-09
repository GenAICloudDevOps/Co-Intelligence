from tortoise import fields
from tortoise.models import Model

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

class BaseModel(Model, TimestampMixin):
    """Base model with timestamps"""
    id = fields.IntField(pk=True)
    
    class Meta:
        abstract = True

class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    is_deleted = fields.BooleanField(default=False)
    deleted_at = fields.DatetimeField(null=True)

