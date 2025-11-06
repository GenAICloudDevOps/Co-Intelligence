from typing import Dict
from apps.agentic_barista.models import MenuItem

class MenuAgent:
    async def process(self, message: str, state: Dict) -> str:
        items = await MenuItem.filter(available=True).all()
        
        if "coffee" in message.lower():
            coffee_items = [item for item in items if item.category == "coffee"]
            response = "☕ **Our Coffee Selection:**\n\n"
            for item in coffee_items:
                response += f"• **{item.name}** - ${float(item.price):.2f}\n  {item.description}\n\n"
            return response
        
        elif "pastry" in message.lower() or "pastries" in message.lower():
            pastry_items = [item for item in items if item.category == "pastry"]
            response = "🥐 **Our Pastries:**\n\n"
            for item in pastry_items:
                response += f"• **{item.name}** - ${float(item.price):.2f}\n  {item.description}\n\n"
            return response
        
        else:
            response = "📋 **Full Menu:**\n\n"
            categories = {}
            for item in items:
                if item.category not in categories:
                    categories[item.category] = []
                categories[item.category].append(item)
            
            for category, cat_items in categories.items():
                response += f"**{category.upper()}:**\n"
                for item in cat_items:
                    response += f"• {item.name} - ${float(item.price):.2f}\n"
                response += "\n"
            
            return response
