import asyncio
import os
import socket

from apps.llms_fine_tuning.job_runner import job_runner
from services.database import close_db, init_db


async def run_worker() -> None:
    await init_db()

    worker_id = os.getenv("FINE_TUNING_WORKER_ID", "").strip() or socket.gethostname()
    poll_seconds = float(os.getenv("FINE_TUNING_POLL_SECONDS", "2.0"))

    try:
        while True:
            run = await job_runner.claim_next(worker_id)
            if run is None:
                await asyncio.sleep(poll_seconds)
                continue
            await job_runner.execute_claimed(run)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(run_worker())

