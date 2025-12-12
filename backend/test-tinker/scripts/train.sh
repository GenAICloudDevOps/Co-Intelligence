#!/usr/bin/env bash
set -euo pipefail

ROOT="${TINKER_BASE_PATH:-/app}"
cd "$ROOT"

# Load local env vars only as a fallback (do not override container/cluster env)
if [[ -z "${TINKER_API_KEY:-}" && -f "./test-tinker/.env" ]]; then
  set -a
  source "./test-tinker/.env"
  set +a
fi

MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.2-1B}"
DATA_FILE="${DATA_FILE:-$ROOT/test-tinker/data/prompt_distillation_lang.jsonl}"
LOG_PATH="$ROOT/test-tinker/runs/prompt-distillation"

PY_BIN="${PY_BIN:-python}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  PY_BIN=python3
fi

if [[ ! -f "$DATA_FILE" ]]; then
  echo "Data file not found at $DATA_FILE. Run scripts/generate_data.sh first." >&2
  exit 1
fi

mkdir -p "$LOG_PATH"

echo "Training student model $MODEL_NAME"
echo "Data: $DATA_FILE"
echo "Logs/checkpoints: $LOG_PATH"

# Mitigate OpenMP shared-memory issues on macOS
export KMP_CREATE_SHM=FALSE
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export TINKER_LOGDIR_BEHAVIOR="${TINKER_LOGDIR_BEHAVIOR:-delete}"

$PY_BIN -m tinker_cookbook.recipes.prompt_distillation.train \
  model_name="$MODEL_NAME" \
  file_path="$DATA_FILE" \
  log_path="$LOG_PATH" \
  behavior_if_log_dir_exists=delete
