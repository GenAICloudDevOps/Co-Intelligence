from typing import Dict
from apps.agentic_barista.models import MenuItem
import re

class OrderAgent:
    async def process(self, message: str, state: Dict) -> str:
        cart = state.get("cart", {})
        
        # Show cart
        if any(word in message.lower() for word in ["cart", "show", "total"]):
            if not cart:
                return "🛒 Your cart is empty. Try adding items like 'add a latte'!"
            
            items = await MenuItem.filter(id__in=list(cart.keys())).all()
            response = "🛒 **Your Cart:**\n\n"
            total = 0
            for item in items:
                quantity = cart[item.id]
                item_total = float(item.price) * quantity
                total += item_total
                response += f"• {quantity}x {item.name} - ${item_total:.2f}\n"
            
            response += f"\n**Total: ${total:.2f}**\n\nSay 'confirm order' to complete your purchase!"
            state["total_amount"] = total
            return response
        
        # Remove from cart
        elif any(word in message.lower() for word in ["remove", "delete"]):
            items = await MenuItem.filter(available=True).all()
            removed = []
            for item in items:
                if item.name.lower() in message.lower() and item.id in cart:
                    del cart[item.id]
                    removed.append(item.name)
            
            if removed:
                state["cart"] = cart
                return f"✅ Removed from cart: {', '.join(removed)}"
            return "❌ Item not found in your cart."
        
        # Add to cart
        else:
            items = await MenuItem.filter(available=True).all()
            added = []
            
            for item in items:
                if item.name.lower() in message.lower():
                    quantity = 1
                    qty_match = re.search(r'(\d+)\s*' + re.escape(item.name.lower()), message.lower())
                    if qty_match:
                        quantity = int(qty_match.group(1))
                    
                    if item.id in cart:
                        cart[item.id] += quantity
                    else:
                        cart[item.id] = quantity
                    
                    added.append(f"{quantity}x {item.name} (${float(item.price):.2f} each)")
            
            if added:
                state["cart"] = cart
                return f"✅ **Added to cart:**\n• " + "\n• ".join(added) + "\n\nSay 'show cart' to see your total!"
            
            return "❌ I couldn't find that item. Try 'show menu' to see what's available."
