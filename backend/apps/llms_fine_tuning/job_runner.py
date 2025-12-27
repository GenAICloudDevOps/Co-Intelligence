import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apps.llms_fine_tuning.models import FineTuningRun
from auth.models import User
from services.email_notifications import email_notifications


@dataclass
class JobConfig:
    key: str
    command: List[str]
    working_dir: Path
    description: str
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class JobRunState:
    run_id: str
    user_id: Optional[int]
    job_key: str
    status: str  # queued | running | success | failed
    start_time: datetime
    end_time: Optional[datetime]
    exit_code: Optional[int]
    output: List[str]
    error: Optional[str] = None
    runtime_env: Dict[str, str] = field(default_factory=dict)
    worker_id: Optional[str] = None
    task: Optional[asyncio.Task] = None
    lines_since_persist: int = 0
    last_persist_monotonic: float = 0.0
    notification_sent: bool = False


class JobRunner:
    def __init__(self):
        base_path = self._resolve_base_path()

        self.workflow_labels = {
            "multilingual": "Multilingual Classification",
            "sft": "Instruction Tuning (SFT)",
            "rl": "RL Mini-App",
        }

        self.jobs: Dict[str, JobConfig] = {
            "multilingual-generate": JobConfig(
                key="multilingual-generate",
                command=["./scripts/generate_data.sh"],
                working_dir=base_path / "test-tinker",
                description="Generate distilled multilingual data",
            ),
            "multilingual-train": JobConfig(
                key="multilingual-train",
                command=["./scripts/train.sh"],
                working_dir=base_path / "test-tinker",
                description="Train multilingual classifier",
            ),
            "multilingual-sample": JobConfig(
                key="multilingual-sample",
                command=["python3", "./sample.py", "--log-path", "./runs/prompt-distillation"],
                working_dir=base_path / "test-tinker",
                description="Run sample.py for predictions",
            ),
            "sft-validate": JobConfig(
                key="sft-validate",
                command=["./scripts/sft_validate.sh"],
                working_dir=base_path / "test-tinker",
                description="Validate instruction tuning (SFT) JSONL dataset",
            ),
            "sft-train": JobConfig(
                key="sft-train",
                command=["./scripts/sft_train.sh"],
                working_dir=base_path / "test-tinker",
                description="Train instruction-tuned model (SFT, cross-entropy)",
            ),
            "sft-sample": JobConfig(
                key="sft-sample",
                command=["python3", "./sample_sft.py", "--log-path", "./runs/instruction-tuning"],
                working_dir=base_path / "test-tinker",
                description="Sample instruction-tuned model",
            ),
            "rl-validate": JobConfig(
                key="rl-validate",
                command=["./scripts/rl_validate.sh"],
                working_dir=base_path / "test-tinker",
                description="Validate RL prompt dataset (JSON formatting tasks)",
            ),
            "rl-train": JobConfig(
                key="rl-train",
                command=["./scripts/rl_train.sh"],
                working_dir=base_path / "test-tinker",
                description="Train with RL (importance sampling) on a reward",
            ),
            "rl-sample": JobConfig(
                key="rl-sample",
                command=["python3", "./sample_rl.py", "--log-path", "./runs/rl-json"],
                working_dir=base_path / "test-tinker",
                description="Sample RL-tuned model",
            ),
        }
        self.runs: Dict[str, JobRunState] = {}
        self._lock = asyncio.Lock()
        self._max_lines = 400
        self._persist_min_interval_s = 0.75
        self._persist_min_lines = 15

    def _resolve_base_path(self) -> Path:
        """Resolve where tm-tinker is located, with sensible fallbacks."""
        candidates = []
        env_path = os.environ.get("TINKER_BASE_PATH")
        if env_path:
            candidates.append(Path(env_path))
        # Common container default
        candidates.append(Path("/app"))
        # Repository-local copy for dev
        candidates.append(Path(__file__).resolve().parents[2])

        for candidate in candidates:
            if candidate.exists():
                return candidate
        # Fallback to first candidate even if missing
        return candidates[0] if candidates else Path("/app/tm-tinker")

    def list_jobs(self) -> List[JobConfig]:
        return list(self.jobs.values())

    def _trim_and_append(self, run: JobRunState, text: str):
        run.output.append(text)
        if len(run.output) > self._max_lines:
            extra = len(run.output) - self._max_lines
            del run.output[0:extra]
        run.lines_since_persist += 1

    async def _persist_run(self, run: JobRunState, force: bool = False):
        """
        Persist run state to the database so polling works across Cloud Run instances.

        Best-effort: never fail the job if persistence fails.
        """
        now = time.monotonic()
        if not force:
            if run.lines_since_persist < self._persist_min_lines and (now - run.last_persist_monotonic) < self._persist_min_interval_s:
                return

        run.last_persist_monotonic = now
        run.lines_since_persist = 0
        try:
            await FineTuningRun.update_or_create(
                defaults={
                    "user_id": run.user_id,
                    "job_key": run.job_key,
                    "status": run.status,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "exit_code": run.exit_code,
                    "output": run.output,
                    "error": run.error,
                    "runtime_env": run.runtime_env or {},
                    "worker_id": run.worker_id,
                    "notification_sent": run.notification_sent,
                },
                run_id=run.run_id,
            )
        except Exception:
            return

    async def _maybe_notify_completion(self, run: JobRunState) -> None:
        if run.notification_sent or not run.job_key.endswith("-train"):
            return
        if not run.user_id:
            return
        user = await User.get_or_none(id=run.user_id)
        if not user or not user.email:
            return

        # Import per-app notification services
        from services.notification_prefs import notification_prefs
        from services.in_app_notifications import in_app_notifications

        app_id = "llms-fine-tuning"
        workflow_key = run.job_key.split("-", 1)[0]
        workflow_label = self.workflow_labels.get(workflow_key, workflow_key)
        model_name = run.runtime_env.get("MODEL_NAME") or "n/a"
        dataset_path = run.runtime_env.get("DATASET_PATH") or run.runtime_env.get("DATA_FILE") or "n/a"
        status_label = "succeeded" if run.status == "success" else "failed"
        end_time = run.end_time.isoformat() + "Z" if run.end_time else datetime.utcnow().isoformat() + "Z"

        # Check per-app email preference
        if await notification_prefs.should_send_email(run.user_id, app_id):
            subject = f"LLM fine-tuning training {status_label}"
            body = (
                f"Hi {user.username},\n\n"
                f"Your fine-tuning training job has {status_label}.\n"
                f"Workflow: {workflow_label}\n"
                f"Step: Train\n"
                f"Job: {run.job_key}\n"
                f"Run ID: {run.run_id}\n"
                f"Status: {status_label}\n"
                f"Model: {model_name}\n"
                f"Dataset: {dataset_path}\n"
                f"Exit code: {run.exit_code if run.exit_code is not None else 'n/a'}\n"
                f"Finished at: {end_time}\n\n"
                "Thanks,\nCo-Intelligence"
            )
            await asyncio.to_thread(email_notifications.send_text_email_safe, user.email, subject, body)

        # Check per-app in-app notification preference
        if await notification_prefs.should_send_in_app(run.user_id, app_id):
            await in_app_notifications.create_notification(
                user_id=run.user_id,
                app_id=app_id,
                title=f"Training {status_label}: {workflow_label}",
                message=f"Your fine-tuning job ({model_name}) has {status_label}.",
                link=f"/apps/llms-fine-tuning?run={run.run_id}",
            )

        run.notification_sent = True

    async def enqueue_run(self, job_key: str, runtime_env: Optional[Dict[str, str]] = None, user_id: Optional[int] = None) -> JobRunState:
        if job_key not in self.jobs:
            raise KeyError(f"Unknown job key: {job_key}")

        run_id = str(uuid.uuid4())
        run = JobRunState(
            run_id=run_id,
            user_id=user_id,
            job_key=job_key,
            status="queued",
            start_time=datetime.utcnow(),
            end_time=None,
            exit_code=None,
            output=[],
            error=None,
            runtime_env=runtime_env or {},
        )

        try:
            await FineTuningRun.update_or_create(
                defaults={
                    "user_id": user_id,
                    "job_key": job_key,
                    "status": run.status,
                    "start_time": run.start_time,
                    "end_time": None,
                    "exit_code": None,
                    "output": [],
                    "error": None,
                    "runtime_env": run.runtime_env or {},
                    "worker_id": None,
                    "notification_sent": False,
                },
                run_id=run_id,
            )
        except Exception:
            pass

        return run

    async def claim_next(self, worker_id: str) -> Optional[JobRunState]:
        """Claim the oldest queued job (best-effort, safe under multiple workers)."""
        try:
            record = await FineTuningRun.filter(status="queued").order_by("start_time").first()
        except Exception:
            return None
        if not record:
            return None

        now = datetime.utcnow()
        try:
            updated = await FineTuningRun.filter(run_id=record.run_id, status="queued").update(
                status="running",
                worker_id=worker_id,
                start_time=now,
            )
        except Exception:
            return None
        if updated != 1:
            return None

        return JobRunState(
            run_id=record.run_id,
            user_id=record.user_id,
            job_key=record.job_key,
            status="running",
            start_time=now,
            end_time=None,
            exit_code=None,
            output=record.output or [],
            error=None,
            runtime_env=record.runtime_env or {},
            worker_id=worker_id,
            notification_sent=bool(record.notification_sent),
        )

    async def execute_claimed(self, run: JobRunState) -> None:
        if run.job_key not in self.jobs:
            run.status = "failed"
            run.error = f"Unknown job key: {run.job_key}"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            await self._maybe_notify_completion(run)
            await self._persist_run(run, force=True)
            return

        config = self.jobs[run.job_key]

        env = os.environ.copy()
        # Allow per-job env overrides (e.g., PYTHONPATH)
        if config.env:
            env.update({k: v for k, v in config.env.items() if v is not None})
        if run.runtime_env:
            env.update({k: v for k, v in run.runtime_env.items() if v is not None})
        try:
            process = await asyncio.create_subprocess_exec(
                *config.command,
                cwd=str(config.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        except FileNotFoundError as exc:
            run.status = "failed"
            run.error = f"Command not found: {exc}"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            await self._maybe_notify_completion(run)
            await self._persist_run(run, force=True)
            return
        except Exception as exc:
            run.status = "failed"
            run.error = f"Failed to start process: {exc}"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            await self._maybe_notify_completion(run)
            await self._persist_run(run, force=True)
            return

        if not process.stdout:
            run.status = "failed"
            run.error = "Process has no stdout"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            await self._maybe_notify_completion(run)
            await self._persist_run(run, force=True)
            return

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                self._trim_and_append(run, text)
                await self._persist_run(run)
            await process.wait()
            run.exit_code = process.returncode
            run.status = "success" if process.returncode == 0 else "failed"
        finally:
            run.end_time = datetime.utcnow()
            await self._maybe_notify_completion(run)
            await self._persist_run(run, force=True)

    async def get_run(self, run_id: str) -> Optional[JobRunState]:
        async with self._lock:
            return self.runs.get(run_id)

    async def get_run_view(self, run_id: str, tail: int = 200) -> Optional[dict]:
        run = await self.get_run(run_id)
        if run:
            output_tail = run.output[-tail:] if tail > 0 else run.output
            return {
                "run_id": run.run_id,
                "job_key": run.job_key,
                "status": run.status,
                "start_time": run.start_time.isoformat() + "Z",
                "end_time": run.end_time.isoformat() + "Z" if run.end_time else None,
                "exit_code": run.exit_code,
                "output": output_tail,
                "error": run.error,
            }

        try:
            record = await FineTuningRun.get_or_none(run_id=run_id)
        except Exception:
            return None
        if not record:
            return None
        output = record.output or []
        output_tail = output[-tail:] if tail > 0 else output
        return {
            "run_id": record.run_id,
            "job_key": record.job_key,
            "status": record.status,
            "start_time": record.start_time.isoformat() + "Z" if record.start_time else None,
            "end_time": record.end_time.isoformat() + "Z" if record.end_time else None,
            "exit_code": record.exit_code,
            "output": output_tail,
            "error": record.error,
        }


job_runner = JobRunner()
