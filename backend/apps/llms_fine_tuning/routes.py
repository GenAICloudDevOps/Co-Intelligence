import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from auth.models import User
from auth.utils import get_current_user
from apps.llms_fine_tuning.job_runner import job_runner

router = APIRouter()


class StartJobRequest(BaseModel):
    job_key: str
    sample_input: str | None = None
    dataset_path: str | None = None
    model_name: str | None = None


def _serialize_job_config(config):
    return {
        "key": config.key,
        "description": config.description,
        "working_dir": str(config.working_dir),
        "command": config.command,
    }

_DATA_ROOT = Path(__file__).resolve().parents[2] / "test-tinker" / "data"
_UPLOAD_ROOT = _DATA_ROOT / "uploads"


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name or "dataset.jsonl"


def _resolve_allowed_dataset_path(requested: str) -> Path:
    candidate = Path(requested).expanduser()
    if not candidate.is_absolute():
        candidate = (_DATA_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed_roots = [_DATA_ROOT.resolve(), _UPLOAD_ROOT.resolve()]
    if not any(str(candidate).startswith(str(root) + os.sep) or candidate == root for root in allowed_roots):
        raise HTTPException(status_code=400, detail="dataset_path must be under test-tinker/data")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=400, detail=f"Dataset not found: {candidate}")
    return candidate


def _count_jsonl_rows(path: Path) -> int:
    rows = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows += 1
    return rows


@router.get("/datasets")
async def list_datasets(current_user: User = Depends(get_current_user)):
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    datasets = []

    built_ins = [
        {
            "id": "prompt_distillation_lang",
            "name": "prompt_distillation_lang.jsonl",
            "path": str((_DATA_ROOT / "prompt_distillation_lang.jsonl").resolve()),
            "description": "Multilingual prompt distillation (≈2100 rows): user text → 2-letter language label",
            "recommended_for": ["multilingual"],
            "built_in": True,
        },
        {
            "id": "instruction_tuning_aws_eks",
            "name": "instruction_tuning_aws_eks.jsonl",
            "path": str((_DATA_ROOT / "instruction_tuning_aws_eks.jsonl").resolve()),
            "description": "Instruction tuning (SFT) examples for AWS EKS Q&A/runbooks (small starter set)",
            "recommended_for": ["sft"],
            "built_in": True,
        },
        {
            "id": "rl_json_formatting_prompts",
            "name": "rl_json_formatting_prompts.jsonl",
            "path": str((_DATA_ROOT / "rl_json_formatting_prompts.jsonl").resolve()),
            "description": "RL prompts with a JSON-format reward (small starter set)",
            "recommended_for": ["rl"],
            "built_in": True,
        },
    ]

    for item in built_ins:
        path = Path(item["path"])
        if path.exists():
            item["rows"] = _count_jsonl_rows(path)
            item["size_bytes"] = path.stat().st_size
        else:
            item["rows"] = 0
            item["size_bytes"] = 0
        datasets.append(item)

    for path in sorted(_UPLOAD_ROOT.glob("*.jsonl")):
        datasets.append(
            {
                "id": f"upload:{path.name}",
                "name": path.name,
                "path": str(path.resolve()),
                "description": "Uploaded dataset",
                "recommended_for": [],
                "built_in": False,
                "rows": _count_jsonl_rows(path),
                "size_bytes": path.stat().st_size,
            }
        )

    return {"datasets": datasets}


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    safe = _safe_filename(file.filename or "dataset.jsonl")
    if not safe.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Only .jsonl files are supported")

    dest = (_UPLOAD_ROOT / safe).resolve()
    # Avoid clobbering: add suffix if needed
    if dest.exists():
        stem = dest.stem
        for i in range(1, 1000):
            candidate = (_UPLOAD_ROOT / f"{stem}-{i}.jsonl").resolve()
            if not candidate.exists():
                dest = candidate
                break

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty upload")
    dest.write_bytes(content)

    return {
        "dataset": {
            "id": f"upload:{dest.name}",
            "name": dest.name,
            "path": str(dest),
            "description": "Uploaded dataset",
            "recommended_for": [],
            "built_in": False,
            "rows": _count_jsonl_rows(dest),
            "size_bytes": dest.stat().st_size,
        }
    }


@router.get("/jobs")
async def list_jobs(current_user: User = Depends(get_current_user)):
    jobs = job_runner.list_jobs()
    return {"jobs": [_serialize_job_config(j) for j in jobs]}


@router.post("/jobs/start")
async def start_job(payload: StartJobRequest, current_user: User = Depends(get_current_user)):
    try:
        runtime_env = {}
        if payload.sample_input:
            runtime_env["SAMPLE_INPUT"] = payload.sample_input
        if payload.model_name:
            runtime_env["MODEL_NAME"] = payload.model_name
        if payload.dataset_path:
            resolved = _resolve_allowed_dataset_path(payload.dataset_path)
            runtime_env["DATASET_PATH"] = str(resolved)
            runtime_env["DATA_FILE"] = str(resolved)
        run = await job_runner.enqueue_run(payload.job_key, runtime_env, user_id=current_user.id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job key not found: {payload.job_key}")

    view = await job_runner.get_run_view(run.run_id, tail=200)
    if not view:
        raise HTTPException(status_code=500, detail="Failed to start job")
    return view


@router.get("/jobs/{run_id}")
async def get_job(run_id: str, tail: int = Query(default=200, ge=0, le=2000), current_user: User = Depends(get_current_user)):
    view = await job_runner.get_run_view(run_id, tail=tail)
    if not view:
        raise HTTPException(status_code=404, detail="Run not found")
    return view
