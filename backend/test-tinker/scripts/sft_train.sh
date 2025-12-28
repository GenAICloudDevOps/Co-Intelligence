#!/usr/bin/env bash
set -euo pipefail

ROOT="${TINKER_BASE_PATH:-}"
if [[ -z "$ROOT" || ! -d "$ROOT/test-tinker" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
cd "$ROOT"

# Load local env vars only as a fallback (do not override container/cluster env)
if [[ -z "${TINKER_API_KEY:-}" && -f "./test-tinker/.env" ]]; then
  set -a
  source "./test-tinker/.env"
  set +a
fi

MODEL_NAME="${MODEL_NAME:-meta-llama/Llama-3.2-1B}"
DATASET_PATH="${DATASET_PATH:-$ROOT/test-tinker/data/instruction_tuning_aws_eks.jsonl}"
LOG_PATH="${LOG_PATH:-$ROOT/test-tinker/runs/instruction-tuning}"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  PY_BIN=python
fi

mkdir -p "$LOG_PATH"

export KMP_CREATE_SHM=FALSE
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export TINKER_LOGDIR_BEHAVIOR="${TINKER_LOGDIR_BEHAVIOR:-delete}"

echo "SFT model: $MODEL_NAME"
echo "Dataset: $DATASET_PATH"
echo "Logs/checkpoints: $LOG_PATH"

$PY_BIN -m tinker_cookbook.recipes.chat_sl.train \
  model_name="$MODEL_NAME" \
  dataset="$DATASET_PATH" \
  log_path="$LOG_PATH" \
  learning_rate="${LEARNING_RATE:-1e-4}" \
  batch_size="${BATCH_SIZE:-64}" \
  lora_rank="${LORA_RANK:-16}" \
  num_epochs="${NUM_EPOCHS:-1}" \
  eval_every="${EVAL_EVERY:-0}" \
  save_every="${SAVE_EVERY:-20}" \
  behavior_if_log_dir_exists=delete
