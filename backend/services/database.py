"""Centralized database service"""
import re
from tortoise import Tortoise
from config import settings

MODEL_MODULES = [
    'auth.models',
    'models.app_role',
    'apps.ai_chat.models',
    'apps.agentic_barista.models',
    'apps.insurance_claims.models',
    'apps.agentic_lms.models',
    'apps.agentic_tutor.models',
    'apps.ml_predictor.models'
]

async def init_db():
    """Initialize database connection"""
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
                        'ssl': None
                    }
                }
            },
            'apps': {
                'models': {
                    'models': MODEL_MODULES,
                    'default_connection': 'default'
                }
            }
        }
        await Tortoise.init(config=db_config)
    else:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': MODEL_MODULES}
        )
    
    await Tortoise.generate_schemas()

async def run_migrations():
    """Run database migrations"""
    conn = Tortoise.get_connection("default")
    
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS global_role VARCHAR(50) DEFAULT 'user'",
        "ALTER TABLE ml_projects ADD COLUMN IF NOT EXISTS current_step VARCHAR(100)",
        "ALTER TABLE ml_projects ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0",
        "ALTER TABLE ml_projects ADD COLUMN IF NOT EXISTS step_logs JSONB DEFAULT '[]'",
        "ALTER TABLE ml_projects ALTER COLUMN target_variable DROP NOT NULL",
        "ALTER TABLE ml_projects ALTER COLUMN target_variable SET DEFAULT ''"
    ]
    
    for sql in migrations:
        try:
            await conn.execute_query(sql)
        except Exception:
            pass

async def close_db():
    """Close database connections"""
    await Tortoise.close_connections()
