"""Centralized database service"""
import re
from tortoise import Tortoise
from config import settings
from apps import load_apps
from apps.registry import registry


def _get_model_modules() -> list[str]:
    """Collect model modules from registered apps plus core models."""
    load_apps()  # Ensure apps are registered even if init_db called directly
    base_modules = ['auth.models', 'models.app_role']
    return base_modules + registry.get_model_modules()

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
                    'models': _get_model_modules(),
                    'default_connection': 'default'
                }
            }
        }
        await Tortoise.init(config=db_config)
    else:
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={'models': _get_model_modules()}
        )
    
    if settings.AUTO_GENERATE_SCHEMAS:
        await Tortoise.generate_schemas()

async def run_migrations():
    """Run database migrations"""
    conn = Tortoise.get_connection("default")
    
    migrations = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS global_role VARCHAR(50) DEFAULT 'user'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN DEFAULT FALSE",
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS password_reset_tokens_user_id_idx ON password_reset_tokens (user_id)",
        "ALTER TABLE ml_projects ADD COLUMN IF NOT EXISTS current_step VARCHAR(100)",
        "ALTER TABLE ml_projects ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0",
        "ALTER TABLE ml_projects ADD COLUMN IF NOT EXISTS step_logs JSONB DEFAULT '[]'",
        "ALTER TABLE ml_projects ALTER COLUMN target_variable DROP NOT NULL",
        "ALTER TABLE ml_projects ALTER COLUMN target_variable SET DEFAULT ''",
        "ALTER TABLE ml_training_runs ADD COLUMN IF NOT EXISTS model_artifact_bucket VARCHAR(255)",
        "ALTER TABLE ml_training_runs ADD COLUMN IF NOT EXISTS model_artifact_key VARCHAR(1024)",
        "ALTER TABLE llms_fine_tuning_runs ADD COLUMN IF NOT EXISTS runtime_env JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE llms_fine_tuning_runs ADD COLUMN IF NOT EXISTS worker_id VARCHAR(128)",
        "ALTER TABLE llms_fine_tuning_runs ADD COLUMN IF NOT EXISTS user_id INTEGER",
        "ALTER TABLE llms_fine_tuning_runs ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE",
        # Evaluation table and columns
        """
        CREATE TABLE IF NOT EXISTS evaluation_results (
            id SERIAL PRIMARY KEY,
            user_id INT,
            app_name VARCHAR(100),
            model_used VARCHAR(200),
            judge_model VARCHAR(200),
            prompt TEXT,
            response TEXT,
            context TEXT,
            helpfulness FLOAT DEFAULT 0,
            grounding FLOAT DEFAULT 0,
            safety FLOAT DEFAULT 0,
            format_compliance FLOAT DEFAULT 0,
            context_precision FLOAT DEFAULT 0,
            context_recall FLOAT DEFAULT 0,
            response_relevancy FLOAT DEFAULT 0,
            faithfulness FLOAT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS context_precision FLOAT DEFAULT 0",
        "ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS context_recall FLOAT DEFAULT 0",
        "ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS response_relevancy FLOAT DEFAULT 0",
        "ALTER TABLE evaluation_results ADD COLUMN IF NOT EXISTS faithfulness FLOAT DEFAULT 0",
        # Data Analysis (App 8)
        "ALTER TABLE data_analysis_datasets ADD COLUMN IF NOT EXISTS last_run_id INTEGER",
        "ALTER TABLE data_analysis_runs ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE",
        # Agentic Tutor - make topic seeding idempotent in multi-pod deployments
        # 1) Re-point references to the lowest id per name
        """
        WITH ranked AS (
            SELECT
                id,
                name,
                ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn,
                MIN(id) OVER (PARTITION BY name) AS keep_id
            FROM tutor_topics
        )
        UPDATE tutor_sessions s
        SET topic_id = r.keep_id
        FROM ranked r
        WHERE s.topic_id = r.id AND r.rn > 1
        """,
        """
        WITH ranked AS (
            SELECT
                id,
                name,
                ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn,
                MIN(id) OVER (PARTITION BY name) AS keep_id
            FROM tutor_topics
        )
        UPDATE tutor_progress p
        SET topic_id = r.keep_id
        FROM ranked r
        WHERE p.topic_id = r.id AND r.rn > 1
        """,
        # 2) Delete duplicate topic rows, keeping the lowest id per name
        """
        DELETE FROM tutor_topics t
        USING (
            SELECT id
            FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn
                FROM tutor_topics
            ) x
            WHERE rn > 1
        ) d
        WHERE t.id = d.id
        """,
        # 3) Prevent future duplicates
        "CREATE UNIQUE INDEX IF NOT EXISTS tutor_topics_name_uniq ON tutor_topics (name)",
        # Per-app notification preferences
        """
        CREATE TABLE IF NOT EXISTS user_app_notification_prefs (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            app_id VARCHAR(50) NOT NULL,
            email_enabled BOOLEAN DEFAULT FALSE,
            in_app_enabled BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, app_id)
        )
        """,
        # In-app notifications
        """
        CREATE TABLE IF NOT EXISTS in_app_notifications (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            app_id VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT,
            link VARCHAR(255),
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS in_app_notifications_user_idx ON in_app_notifications(user_id, is_read, created_at DESC)"
    ]
    
    for sql in migrations:
        try:
            await conn.execute_query(sql)
        except Exception:
            pass

async def close_db():
    """Close database connections"""
    await Tortoise.close_connections()
