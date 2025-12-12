#!/usr/bin/env bash
set -euo pipefail

ROOT="${TINKER_BASE_PATH:-/app}"
WORKDIR="$ROOT/test-tinker"
cd "$WORKDIR"

# Load local env vars only as a fallback (do not override container/cluster env)
if [[ -z "${TINKER_API_KEY:-}" && -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

OUTPUT_FILE="$WORKDIR/data/prompt_distillation_lang.jsonl"
mkdir -p "$(dirname "$OUTPUT_FILE")"

PY_BIN="${PY_BIN:-python}"
if ! command -v "$PY_BIN" >/dev/null 2>&1; then
  PY_BIN=python3
fi

echo "Generating distilled data to $OUTPUT_FILE"
$PY_BIN -m tinker_cookbook.recipes.prompt_distillation.create_data \
  output_file="$OUTPUT_FILE"

echo "Done. Sample of file:"
head -n 2 "$OUTPUT_FILE" || true
