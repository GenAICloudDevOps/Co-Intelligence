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

    # Add email notifications preference to users if not exists
    try:
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN DEFAULT FALSE"
        )
        print("✓ Added email_notifications_enabled to users")
    except Exception as e:
        print(f"⚠ users email_notifications_enabled: {e}")

    # Add Slack notifications preference to users if not exists
    try:
        await conn.execute_query(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS slack_notifications_enabled BOOLEAN DEFAULT FALSE"
        )
        print("✓ Added slack_notifications_enabled to users")
    except Exception as e:
        print(f"⚠ users slack_notifications_enabled: {e}")

    # Notification delivery outbox
    try:
        await conn.execute_query(
            """
            CREATE TABLE IF NOT EXISTS notification_deliveries (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE SET NULL,
                channel VARCHAR(20) NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                app_id VARCHAR(50),
                idempotency_key VARCHAR(255) UNIQUE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 5,
                next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                last_error TEXT,
                provider_response TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                sent_at TIMESTAMPTZ
            )
            """
        )
        await conn.execute_query(
            "CREATE INDEX IF NOT EXISTS notification_deliveries_status_idx ON notification_deliveries(status, next_attempt_at)"
        )
        await conn.execute_query(
            "CREATE INDEX IF NOT EXISTS notification_deliveries_user_idx ON notification_deliveries(user_id, created_at DESC)"
        )
        print("✓ Added notification_deliveries")
    except Exception as e:
        print(f"⚠ notification_deliveries: {e}")
    
    await Tortoise.close_connections()
    print("✅ Migration complete")

if __name__ == "__main__":
    asyncio.run(migrate())
