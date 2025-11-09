"""
Unified database initialization script
Run this to seed all app data
"""
import asyncio
from tortoise import Tortoise
from config import settings

# Import apps to trigger registration
import apps.ai_chat
import apps.agentic_barista
import apps.insurance_claims
import apps.agentic_lms
import apps.agentic_tutor

from apps.registry import registry

async def init_all():
    """Initialize database and seed all apps"""
    print("🔧 Initializing database...")
    
    # Build model modules list from registry
    model_modules = ['auth.models', 'models.app_role'] + registry.get_model_modules()
    
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': model_modules}
    )
    
    print("✓ Database connected")
    
    # Generate schemas
    print("📋 Generating schemas...")
    await Tortoise.generate_schemas()
    print("✓ Schemas created")
    
    # Initialize all apps
    print("\n🚀 Initializing apps...")
    await registry.initialize_apps()
    print("✓ All apps initialized")
    
    # Optional: Run seed scripts
    print("\n🌱 Seeding data...")
    
    # Seed barista menu
    try:
        from apps.agentic_barista.seed_menu import seed_menu
        await seed_menu()
        print("✓ Barista menu seeded")
    except Exception as e:
        print(f"⚠ Barista seed skipped: {e}")
    
    # Seed insurance users
    try:
        from seed_insurance_users import seed_users
        await seed_users()
        print("✓ Insurance users seeded")
    except Exception as e:
        print(f"⚠ Insurance seed skipped: {e}")
    
    # Seed tutor topics
    try:
        from apps.agentic_tutor.seed_topics import seed_topics
        await seed_topics()
        print("✓ Tutor topics seeded")
    except Exception as e:
        print(f"⚠ Tutor topics seed skipped: {e}")
    
    await Tortoise.close_connections()
    print("\n✅ Initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_all())
