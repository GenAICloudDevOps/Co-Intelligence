import asyncio

from config import settings
from services.database import init_db, run_migrations, close_db
from services.notification_delivery import notification_delivery_worker


async def main() -> None:
    if not settings.NOTIFICATION_WORKER_ENABLED:
        print("Notification worker disabled (NOTIFICATION_WORKER_ENABLED=false).")
        return

    print("=== NOTIFICATION WORKER START ===")
    try:
        await init_db()
        await run_migrations()
        print("✓ Database ready")
        await notification_delivery_worker.run()
    finally:
        await close_db()
        print("=== NOTIFICATION WORKER STOP ===")


if __name__ == "__main__":
    asyncio.run(main())
