#!/usr/bin/env bash
set -euo pipefail

ROOT="${TINKER_BASE_PATH:-/app}"
cd "$ROOT/test-tinker"

# Load local env vars only as a fallback (do not override container/cluster env)
if [[ -z "${TINKER_API_KEY:-}" && -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

export MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.2-1B}"
export DATASET_PATH="${DATASET_PATH:-$ROOT/test-tinker/data/rl_json_formatting_prompts.jsonl}"
export LOG_PATH="${LOG_PATH:-$ROOT/test-tinker/runs/rl-json}"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  PY_BIN=python
fi

mkdir -p "$LOG_PATH"

export KMP_CREATE_SHM=FALSE
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"

echo "RL model: $MODEL_NAME"
echo "Dataset: $DATASET_PATH"
echo "Logs/checkpoints: $LOG_PATH"

$PY_BIN ./rl_train_importance_sampling.py
