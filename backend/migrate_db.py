import asyncio
from tortoise import Tortoise
from config import settings

async def migrate():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': ['auth.models', 'apps.ai_chat.models', 'apps.agentic_barista.models']}
    )
    
    conn = Tortoise.get_connection("default")
    
    # Add updated_at column to all tables if not exists
    tables = [
        "users",
        "chat_sessions", 
        "chat_messages",
        "chat_documents",
        "barista_menu_items",
        "barista_orders"
    ]
    
    for table in tables:
        try:
            await conn.execute_query(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            )
            print(f"✓ Added updated_at to {table}")
        except Exception as e:
            print(f"⚠ {table}: {e}")
    
    # Add role column to users if not exists
    try:
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user'"
        )
        print("✓ Added role to users")
    except Exception as e:
        print(f"⚠ users role: {e}")
    
    await Tortoise.close_connections()
    print("✅ Migration complete")

if __name__ == "__main__":
    asyncio.run(migrate())
