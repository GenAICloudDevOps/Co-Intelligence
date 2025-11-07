import asyncio
from tortoise import Tortoise
from config import settings
from auth.models import User
from models.app_role import AppRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_users():
    """Create test users with different roles for insurance claims"""
    
    # Check if users already exist
    existing_admin = await User.get_or_none(email="admin@test.com")
    if existing_admin:
        print("✅ Test users already exist")
        return
    
    # 1. Admin user (platform admin)
    admin = await User.create(
        email="admin@test.com",
        username="admin",
        hashed_password=pwd_context.hash("password"),
        global_role="admin",
        is_active=True
    )
    print(f"✅ Created admin user: admin@test.com / password")
    
    # 2. Agent user
    agent = await User.create(
        email="agent@test.com",
        username="agent",
        hashed_password=pwd_context.hash("password"),
        global_role="user",
        is_active=True
    )
    await AppRole.create(user_id=agent.id, app_name="insurance-claims", role="agent")
    print(f"✅ Created agent user: agent@test.com / password")
    
    # 3. Adjuster user
    adjuster = await User.create(
        email="adjuster@test.com",
        username="adjuster",
        hashed_password=pwd_context.hash("password"),
        global_role="user",
        is_active=True
    )
    await AppRole.create(user_id=adjuster.id, app_name="insurance-claims", role="adjuster")
    print(f"✅ Created adjuster user: adjuster@test.com / password")
    
    # 4. Manager user
    manager = await User.create(
        email="manager@test.com",
        username="manager",
        hashed_password=pwd_context.hash("password"),
        global_role="user",
        is_active=True
    )
    await AppRole.create(user_id=manager.id, app_name="insurance-claims", role="manager")
    print(f"✅ Created manager user: manager@test.com / password")
    
    # 5. Customer user (for testing)
    customer = await User.create(
        email="customer@test.com",
        username="customer",
        hashed_password=pwd_context.hash("password"),
        global_role="user",
        is_active=True
    )
    await AppRole.create(user_id=customer.id, app_name="insurance-claims", role="customer")
    print(f"✅ Created customer user: customer@test.com / password")
    
    print("\n🎉 All test users created successfully!")
    print("\nLogin credentials:")
    print("  admin@test.com / password     → Platform Admin")
    print("  agent@test.com / password     → Agent")
    print("  adjuster@test.com / password  → Adjuster")
    print("  manager@test.com / password   → Manager")
    print("  customer@test.com / password  → Customer")

async def main():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={'models': [
            'auth.models',
            'apps.ai_chat.models',
            'apps.agentic_barista.models',
            'apps.insurance_claims.models',
            'models.app_role'
        ]}
    )
    await seed_users()
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
