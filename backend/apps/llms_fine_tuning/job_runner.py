import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


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
            return
        except Exception as exc:
            run.status = "failed"
            run.error = f"Failed to start process: {exc}"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            return

        if not process.stdout:
            run.status = "failed"
            run.error = "Process has no stdout"
            run.end_time = datetime.utcnow()
            run.exit_code = -1
            return

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                self._trim_and_append(run, text)
            await process.wait()
            run.exit_code = process.returncode
            run.status = "success" if process.returncode == 0 else "failed"
        finally:
            run.end_time = datetime.utcnow()

    async def get_run(self, run_id: str) -> Optional[JobRunState]:
        async with self._lock:
            return self.runs.get(run_id)

    async def get_run_view(self, run_id: str, tail: int = 200) -> Optional[dict]:
        run = await self.get_run(run_id)
        if not run:
            return None
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


job_runner = JobRunner()
