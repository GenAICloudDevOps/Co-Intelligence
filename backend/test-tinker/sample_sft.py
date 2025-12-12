#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import tinker
from tinker_cookbook import model_info, renderers
from tinker_cookbook.tokenizer_utils import get_tokenizer


def load_model_name(log_path: Path, override: str | None) -> str:
    if override:
        return override
    config_path = log_path / "config.json"
    if config_path.exists():
        with config_path.open() as f:
            cfg = json.load(f)
        if "model_name" in cfg:
            return cfg["model_name"]
    raise FileNotFoundError("Could not infer model_name. Pass --model-name or ensure config.json exists.")


def load_latest_sampler_path(log_path: Path) -> str:
    ckpt_path = log_path / "checkpoints.jsonl"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"No checkpoints.jsonl found in {log_path}")

    sampler = None
    with ckpt_path.open() as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "sampler_path" in row:
                sampler = row["sampler_path"]
    if sampler is None:
        raise RuntimeError("No sampler_path entries found in checkpoints.jsonl")
    return sampler


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-path", required=True, help="Path to SFT training log dir")
    ap.add_argument("--model-name", help="Base model name (overrides config.json)")
    ap.add_argument("--prompt", help="User question/prompt to ask the fine-tuned model")
    args = ap.parse_args()

    env_override = os.getenv("SAMPLE_INPUT")
    prompt = (env_override or args.prompt or "").strip()
    if not prompt:
        raise SystemExit("Provide --prompt or set SAMPLE_INPUT")

    log_path = Path(args.log_path).expanduser().resolve()
    model_name = load_model_name(log_path, args.model_name)
    sampler_path = load_latest_sampler_path(log_path)

    renderer_name = model_info.get_recommended_renderer_name(model_name)
    tokenizer = get_tokenizer(model_name)
    renderer = renderers.get_renderer(renderer_name, tokenizer)

    load_env_file(Path(__file__).resolve().parent / ".env")
    if not os.environ.get("TINKER_API_KEY"):
        raise RuntimeError("TINKER_API_KEY is not set. Export it or add it to test-tinker/.env.")

    service = tinker.ServiceClient()
    sampling_client = service.create_sampling_client(base_model=model_name, model_path=sampler_path)

    sampling_params = tinker.SamplingParams(
        max_tokens=int(os.getenv("SFT_MAX_TOKENS", "512")),
        temperature=float(os.getenv("SFT_TEMPERATURE", "0.2")),
        stop=renderer.get_stop_sequences(),
    )

    convo = [{"role": "user", "content": prompt}]
    model_input = renderer.build_generation_prompt(convo)
    result = sampling_client.sample(prompt=model_input, num_samples=1, sampling_params=sampling_params).result()
    tokens = result.sequences[0].tokens
    message, _ok = renderer.parse_response(tokens)

    print(f"Model: {model_name}")
    print(f"Sampler: {sampler_path}")
    print("====================================")
    print(prompt)
    print("----")
    print(message["content"].strip())


if __name__ == "__main__":
    main()

