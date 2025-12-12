# Prompt Distillation Mini-Project

This folder walks you through a tiny, end-to-end run:

- Generate a small multilingual classification dataset (teacher model does the labeling).
- Fine-tune a compact base model with LoRA via the cookbook’s prompt-distillation recipe.
- Manually sample a few lines to confirm the 2-letter language labels.

## Prerequisites
- Set `TINKER_API_KEY` in your shell.
- In the repo root, install deps (recommended): `uv pip install -e ./tinker-cookbook`
- Optional: `export PYTHONPATH="$(pwd)/tinker-cookbook:${PYTHONPATH}"` if you prefer not to install.

## Paths used here
- Data: `./data/prompt_distillation_lang.jsonl`
- Run logs/checkpoints: `./runs/prompt-distillation`

## 1) Generate distilled data (teacher)
```bash
cd /Users/gayathri/documents/python/venkat/tm-tinker
./test-tinker/scripts/generate_data.sh
```
This calls the built-in generator (`recipes/prompt_distillation/create_data.py`) and writes a JSONL of user → 2-letter language code pairs.

## 2) Fine-tune a small model (student)
Pick a compact base model (default in the script: `meta-llama/Llama-3.2-1B`). Then run:
```bash
./test-tinker/scripts/train.sh
```
Checkpoints + metrics land in `./runs/prompt-distillation`.

## 3) Quick manual eval
After training finishes, sample a few multilingual strings:
```bash
python ./test-tinker/sample.py --log-path ./runs/prompt-distillation
```
You should see outputs like `en`, `fr`, `zh`, `ar`, etc. (`ar, de, el, en, es, fr, hi, ru, tr, ur, vi, zh, ot`).

## Notes / knobs
- Change the base model: edit `MODEL_NAME` in `scripts/train.sh`.
- Change where logs go: edit `LOG_PATH` in `scripts/train.sh`.
- Want more data? Adjust `OUTPUT_FILE` in `scripts/generate_data.sh`.
- Sampling uses the most recent `sampler_path` in `checkpoints.jsonl`. Pass `--model-name` to `sample.py` to override autodetection.
