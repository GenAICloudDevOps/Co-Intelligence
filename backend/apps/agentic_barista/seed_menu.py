from tortoise import Tortoise
from apps.agentic_barista.models import MenuItem
import asyncio
import os

async def seed_menu():
    # Initialize database
    db_url = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
    
    await Tortoise.init(
        db_url=db_url,
        modules={'models': ['apps.agentic_barista.models']}
    )
    await Tortoise.generate_schemas()
    
    # Check if menu already exists
    existing = await MenuItem.all().count()
    if existing > 0:
        print(f"Menu already seeded with {existing} items")
        await Tortoise.close_connections()
        return
    
    # Seed menu items
    menu_items = [
        {"name": "Espresso", "description": "Rich, bold shot of espresso", "price": 2.50, "category": "coffee"},
        {"name": "Americano", "description": "Espresso with hot water", "price": 3.00, "category": "coffee"},
        {"name": "Latte", "description": "Espresso with steamed milk and foam", "price": 4.50, "category": "coffee"},
        {"name": "Cappuccino", "description": "Equal parts espresso, steamed milk, and foam", "price": 4.00, "category": "coffee"},
        {"name": "Mocha", "description": "Espresso with chocolate and steamed milk", "price": 5.00, "category": "coffee"},
        {"name": "Croissant", "description": "Buttery, flaky French pastry", "price": 3.50, "category": "pastry"},
        {"name": "Blueberry Muffin", "description": "Fresh baked muffin with blueberries", "price": 3.00, "category": "pastry"},
        {"name": "Chocolate Chip Cookie", "description": "Warm chocolate chip cookie", "price": 2.50, "category": "pastry"},
        {"name": "Avocado Toast", "description": "Toasted bread with fresh avocado", "price": 6.00, "category": "food"},
        {"name": "Bagel with Cream Cheese", "description": "Fresh bagel with cream cheese", "price": 4.50, "category": "food"},
    ]
    
    for item_data in menu_items:
        await MenuItem.create(**item_data)
    
    print(f"✅ Seeded {len(menu_items)} menu items")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(seed_menu())
