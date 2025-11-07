from tortoise import fields
from models.base import BaseModel

class MenuItem(BaseModel):
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    category = fields.CharField(max_length=50)
    available = fields.BooleanField(default=True)

    class Meta:
        table = "barista_menu_items"

class Order(BaseModel):
    session_id = fields.CharField(max_length=255)
    user_id = fields.IntField(null=True)
    items = fields.JSONField()
    total = fields.DecimalField(max_digits=10, decimal_places=2)
    status = fields.CharField(max_length=50, default="confirmed")

    class Meta:
        table = "barista_orders"
