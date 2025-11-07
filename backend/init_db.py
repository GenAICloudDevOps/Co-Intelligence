import asyncio
from tortoise import Tortoise
from config import settings
from apps.agentic_barista.seed_menu import seed_menu

async def migrate():
    """Run database migrations"""
    conn = Tortoise.get_connection("default")
    
    tables = ["users", "chat_sessions", "chat_messages", "chat_documents", "barista_menu_items", "barista_orders"]
    
    for table in tables:
        try:
            await conn.execute_query(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
        except:
            pass
    
    try:
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user'"
        )
    except:
        pass

async def init():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': ['auth.models', 'apps.ai_chat.models', 'apps.agentic_barista.models']}
    )
    await Tortoise.generate_schemas()
    await migrate()
    await seed_menu()
    await Tortoise.close_connections()
    print("✅ Database initialized and menu seeded")

if __name__ == "__main__":
    asyncio.run(init())
