from tortoise import fields
from tortoise.models import Model

class MenuItem(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    category = fields.CharField(max_length=50)
    available = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "barista_menu_items"

class Order(Model):
    id = fields.IntField(pk=True)
    session_id = fields.CharField(max_length=255)
    user_id = fields.IntField(null=True)
    items = fields.JSONField()
    total = fields.DecimalField(max_digits=10, decimal_places=2)
    status = fields.CharField(max_length=50, default="confirmed")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "barista_orders"
