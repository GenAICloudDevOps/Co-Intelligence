import asyncio
import re
from tortoise import Tortoise
from config import settings
from apps.agentic_barista.seed_menu import seed_menu

async def migrate():
    """Run database migrations"""
    conn = Tortoise.get_connection("default")
    
    # Rename role to global_role in users table
    try:
        await conn.execute_query(
            "ALTER TABLE users RENAME COLUMN role TO global_role"
        )
        print("✅ Renamed users.role to users.global_role")
    except:
        # Column might already be renamed or doesn't exist
        try:
            await conn.execute_query(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS global_role VARCHAR(50) DEFAULT 'user'"
            )
        except:
            pass
    
    print("✅ Database migrations completed")

async def seed_test_roles():
    """Seed test app roles for insurance claims"""
    from models.app_role import AppRole
    from auth.models import User
    
    # Get first user (if exists)
    user = await User.first()
    if user:
        # Check if already has customer role
        existing = await AppRole.get_or_none(user_id=user.id, app_name="insurance-claims", role="customer")
        if not existing:
            await AppRole.create(user_id=user.id, app_name="insurance-claims", role="customer")
            print(f"✅ Assigned customer role to user {user.username}")

async def init():
    # Parse DATABASE_URL and disable SSL
    db_url = settings.DATABASE_URL
    match = re.match(r'postgres://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)', db_url)
    
    if match:
        user, password, host, port, database = match.groups()
        db_config = {
            'connections': {
                'default': {
                    'engine': 'tortoise.backends.asyncpg',
                    'credentials': {
                        'host': host,
                        'port': int(port),
                        'user': user,
                        'password': password,
                        'database': database,
                        'ssl': None  # Disable SSL
                    }
                }
            },
            'apps': {
                'models': {
                    'models': [
                        'auth.models',
                        'apps.ai_chat.models',
                        'apps.agentic_barista.models',
                        'apps.insurance_claims.models',
                        'apps.agentic_lms.models',
                        'models.app_role'
                    ],
                    'default_connection': 'default'
                }
            }
        }
        await Tortoise.init(config=db_config)
    else:
        # Fallback
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': [
                'auth.models',
                'apps.ai_chat.models',
                'apps.agentic_barista.models',
                'apps.insurance_claims.models',
                'apps.agentic_lms.models',
                'models.app_role'
            ]}
        )
    
    await Tortoise.generate_schemas()
    await migrate()
    await seed_menu()
    await seed_test_roles()
    await Tortoise.close_connections()
    print("✅ Database initialized, menu seeded, and test roles created")

if __name__ == "__main__":
    asyncio.run(init())
