from typing import Dict
from apps.agentic_barista.models import MenuItem, Order

class ConfirmationAgent:
    async def process(self, message: str, state: Dict) -> str:
        cart = state.get("cart", {})
        session_id = state.get("session_id", "default")
        
        if not cart:
            return "❌ Your cart is empty! Add items first before confirming."
        
        # Calculate total
        items = await MenuItem.filter(id__in=list(cart.keys())).all()
        total = 0
        order_items = []
        
        for item in items:
            quantity = cart[item.id]
            item_total = float(item.price) * quantity
            total += item_total
            order_items.append({
                "id": item.id,
                "name": item.name,
                "quantity": quantity,
                "price": float(item.price),
                "total": item_total
            })
        
        # Save order
        order = await Order.create(
            session_id=session_id,
            items=order_items,
            total=total,
            status="confirmed"
        )
        
        # Clear cart
        state["cart"] = {}
        state["total_amount"] = 0
        
        # Build response
        response = f"✅ **Order Confirmed!** (Order #{order.id})\n\n"
        response += "**Items:**\n"
        for item_data in order_items:
            response += f"• {item_data['quantity']}x {item_data['name']} - ${item_data['total']:.2f}\n"
        response += f"\n**Total: ${total:.2f}**\n\n"
        response += "Your order will be ready in 10-15 minutes. Thank you! ☕"
        
        return response
