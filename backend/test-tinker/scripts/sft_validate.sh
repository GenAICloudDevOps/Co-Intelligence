#!/usr/bin/env bash
set -euo pipefail

ROOT="${TINKER_BASE_PATH:-/app}"
cd "$ROOT/test-tinker"

if [[ -z "${TINKER_API_KEY:-}" && -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

DATASET_PATH="${DATASET_PATH:-$ROOT/test-tinker/data/instruction_tuning_aws_eks.jsonl}"

PY_BIN="${PY_BIN:-python3}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  PY_BIN=python
fi

export DATASET_PATH
echo "Validating chat dataset: $DATASET_PATH"
$PY_BIN ./validate_chat_dataset.py
