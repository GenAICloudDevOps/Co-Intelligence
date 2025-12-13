import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from apps.llms_fine_tuning.models import FineTuningRun


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
    job_key: str
    status: str  # idle | running | success | failed
    start_time: datetime
    end_time: Optional[datetime]
    exit_code: Optional[int]
    output: List[str]
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None
    lines_since_persist: int = 0
    last_persist_monotonic: float = 0.0


class JobRunner:
    def __init__(self):
        base_path = self._resolve_base_path()

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
                    "job_key": run.job_key,
                    "status": run.status,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "exit_code": run.exit_code,
                    "output": run.output,
                    "error": run.error,
                },
                run_id=run.run_id,
            )
        except Exception:
            return

    async def start_run(self, job_key: str, runtime_env: Optional[Dict[str, str]] = None) -> JobRunState:
        if job_key not in self.jobs:
            raise KeyError(f"Unknown job key: {job_key}")

        run_id = str(uuid.uuid4())
        run = JobRunState(
            run_id=run_id,
            job_key=job_key,
            status="running",
            start_time=datetime.utcnow(),
            end_time=None,
            exit_code=None,
            output=[],
            error=None,
        )
        async with self._lock:
            self.runs[run_id] = run

        try:
            await FineTuningRun.update_or_create(
                defaults={
                    "job_key": job_key,
                    "status": run.status,
                    "start_time": run.start_time,
                    "end_time": None,
                    "exit_code": None,
                    "output": [],
                    "error": None,
                },
                run_id=run_id,
            )
        except Exception:
            pass

        run.task = asyncio.create_task(self._execute_run(run_id, self.jobs[job_key], runtime_env))
        return run

    async def _execute_run(self, run_id: str, config: JobConfig, runtime_env: Optional[Dict[str, str]] = None):
        run = self.runs.get(run_id)
        if not run:
            return

        env = os.environ.copy()
        # Allow per-job env overrides (e.g., PYTHONPATH)
        if config.env:
            env.update({k: v for k, v in config.env.items() if v is not None})
        if runtime_env:
            env.update({k: v for k, v in runtime_env.items() if v is not None})
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
            await self._persist_run(run, force=True)
            return
        except Exception as exc:
            run.status = "failed"
            run.error = f"Failed to start process: {exc}"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            await self._persist_run(run, force=True)
            return

        if not process.stdout:
            run.status = "failed"
            run.error = "Process has no stdout"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
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
