#!/usr/bin/env python3
"""
Lightweight sampler to sanity-check the distilled language classifier.

Usage:
  python sample.py --log-path ./runs/prompt-distillation
  python sample.py --log-path ./runs/prompt-distillation --model-name meta-llama/Llama-3.2-1B
"""

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
    raise FileNotFoundError(
        "Could not infer model_name. Pass --model-name or ensure config.json exists."
    )


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
    """Load simple KEY=VALUE lines from a .env file if present."""
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
    ap.add_argument("--log-path", required=True, help="Path to training log dir")
    ap.add_argument("--model-name", help="Base model name (overrides config.json)")
    ap.add_argument(
        "--examples",
        nargs="*",
        default=[
            "Hello, how are you?",
            "Bonjour, comment allez-vous?",
            "你好，这周末有空吗？",
            "مرحبا كيف حالك اليوم؟",
            "Guten Tag, ich heiße Anna.",
            "Xin chào, hôm nay bạn ổn chứ?",
            "¿Dónde está la biblioteca?",
        ],
        help="Custom test strings",
    )
    args = ap.parse_args()

    env_override = os.getenv("SAMPLE_INPUT")
    if env_override:
        args.examples = [env_override.strip()]

    log_path = Path(args.log_path).expanduser().resolve()
    model_name = load_model_name(log_path, args.model_name)
    sampler_path = load_latest_sampler_path(log_path)

    renderer_name = model_info.get_recommended_renderer_name(model_name)
    tokenizer = get_tokenizer(model_name)
    renderer = renderers.get_renderer(renderer_name, tokenizer)

    # Load TINKER_API_KEY from the local .env if it has not been exported.
    load_env_file(Path(__file__).resolve().parent / ".env")
    if not os.environ.get("TINKER_API_KEY"):
        raise RuntimeError(
            "TINKER_API_KEY is not set. Export it in your shell or add it to test-tinker/.env."
        )

    service = tinker.ServiceClient()
    sampling_client = service.create_sampling_client(
        base_model=model_name,
        model_path=sampler_path,
    )

    print(f"Using model: {model_name}")
    print(f"Renderer: {renderer_name}")
    print(f"Sampler checkpoint: {sampler_path}")
    print("====================================")

    sampling_params = tinker.SamplingParams(
        max_tokens=8,
        temperature=0.0,
        stop=renderer.get_stop_sequences(),
    )

    for text in args.examples:
        model_input = renderer.build_generation_prompt([{"role": "user", "content": text}])
        result = sampling_client.sample(
            prompt=model_input,
            num_samples=1,
            sampling_params=sampling_params,
        ).result()
        tokens = result.sequences[0].tokens
        message, _ok = renderer.parse_response(tokens)
        print(f"Input: {text}")
        print(f"Predicted label: {message['content'].strip()}")
        print("---")


if __name__ == "__main__":
    main()
