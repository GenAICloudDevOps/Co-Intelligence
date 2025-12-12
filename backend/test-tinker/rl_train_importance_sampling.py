#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import tinker
import torch
from tinker import types
from tinker.types.tensor_data import TensorData
from tinker_cookbook import model_info, renderers
from tinker_cookbook.tokenizer_utils import get_tokenizer


@dataclass
class RunConfig:
    model_name: str
    dataset_path: str
    log_path: str
    lora_rank: int = 16
    learning_rate: float = 5e-5
    batch_size: int = 4
    group_size: int = 4
    max_tokens: int = 256
    save_every: int = 5


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


def read_dataset(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def reward_json_required_keys(text: str, required_keys: list[str]) -> float:
    try:
        obj = json.loads(text)
    except Exception:
        return 0.0
    if not isinstance(obj, dict):
        return 0.0
    found = 0
    for key in required_keys:
        if key in obj:
            found += 1
    # Shaped reward to avoid all-zeros advantages early in training.
    return 0.25 + 0.75 * (found / max(1, len(required_keys)))


def write_checkpoint_row(
    log_path: Path, name: str, sampler_path: str, step: int, state_path: str | None = None
) -> None:
    ckpt_path = log_path / "checkpoints.jsonl"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "name": name,
        "step": step,
        "state_path": state_path,
        "sampler_path": sampler_path,
    }
    with ckpt_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def main() -> None:
    load_env_file(Path(__file__).resolve().parent / ".env")
    if not os.environ.get("TINKER_API_KEY"):
        raise RuntimeError("TINKER_API_KEY is not set. Export it or add it to test-tinker/.env.")

    cfg = RunConfig(
        model_name=os.getenv("MODEL_NAME", "meta-llama/Llama-3.2-1B"),
        dataset_path=os.environ["DATASET_PATH"],
        log_path=os.getenv("LOG_PATH", str(Path("./runs/rl-json").resolve())),
        lora_rank=int(os.getenv("LORA_RANK", "16")),
        learning_rate=float(os.getenv("LEARNING_RATE", "5e-5")),
        batch_size=int(os.getenv("BATCH_SIZE", "4")),
        group_size=int(os.getenv("GROUP_SIZE", "4")),
        max_tokens=int(os.getenv("MAX_TOKENS", "256")),
        save_every=int(os.getenv("SAVE_EVERY", "5")),
    )

    log_path = Path(cfg.log_path).expanduser().resolve()
    log_path.mkdir(parents=True, exist_ok=True)
    (log_path / "config.json").write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")

    dataset_path = Path(cfg.dataset_path).expanduser().resolve()
    rows = read_dataset(dataset_path)
    if not rows:
        raise RuntimeError(f"Empty dataset: {dataset_path}")

    renderer_name = model_info.get_recommended_renderer_name(cfg.model_name)
    tokenizer = get_tokenizer(cfg.model_name)
    renderer = renderers.get_renderer(renderer_name, tokenizer)

    service_client = tinker.ServiceClient()
    training_client = service_client.create_lora_training_client(base_model=cfg.model_name, rank=cfg.lora_rank)

    sampling_params = tinker.types.SamplingParams(
        max_tokens=cfg.max_tokens,
        temperature=float(os.getenv("SAMPLING_TEMPERATURE", "0.8")),
        stop=renderer.get_stop_sequences(),
    )
    adam_params = types.AdamParams(learning_rate=cfg.learning_rate, beta1=0.9, beta2=0.95, eps=1e-8)

    n_steps = max(1, len(rows) // cfg.batch_size)
    print(f"RL(importance_sampling) steps: {n_steps}  batch_size={cfg.batch_size} group_size={cfg.group_size}")
    print(f"Dataset: {dataset_path}")
    print(f"Log path: {log_path}")
    print(f"Model: {cfg.model_name} (LoRA rank {cfg.lora_rank})")
    print("====================================")

    for step in range(n_steps):
        t0 = time.time()
        batch = rows[step * cfg.batch_size : (step + 1) * cfg.batch_size]

        sampling_path = training_client.save_weights_for_sampler(name=f"{step:06d}").result().path
        sampling_client = service_client.create_sampling_client(base_model=cfg.model_name, model_path=sampling_path)

        training_datums: list[types.Datum] = []
        batch_rewards: list[float] = []
        for row in batch:
            prompt_text = row["prompt"]
            required_keys = row["required_keys"]

            convo = [{"role": "user", "content": prompt_text}]
            model_input = renderer.build_generation_prompt(convo)
            prompt_tokens = model_input.to_ints()

            group_rewards: list[float] = []
            group_tokens: list[list[int]] = []
            group_logprobs: list[list[float]] = []
            group_ob_lens: list[int] = []

            for _ in range(cfg.group_size):
                res = sampling_client.sample(prompt=model_input, num_samples=1, sampling_params=sampling_params).result()
                sampled_tokens = res.sequences[0].tokens
                sampled_logprobs = res.sequences[0].logprobs
                if sampled_logprobs is None:
                    continue

                all_tokens = prompt_tokens + sampled_tokens
                group_tokens.append(all_tokens)
                group_ob_lens.append(len(prompt_tokens) - 1)
                group_logprobs.append(sampled_logprobs)

                message, _ok = renderer.parse_response(sampled_tokens)
                reward = reward_json_required_keys(message["content"], required_keys)
                group_rewards.append(reward)

            if not group_rewards:
                continue

            baseline = sum(group_rewards) / len(group_rewards)
            advantages = [r - baseline for r in group_rewards]
            batch_rewards.append(baseline)

            if all(a == 0.0 for a in advantages):
                continue

            for tokens, logprob, advantage, ob_len in zip(group_tokens, group_logprobs, advantages, group_ob_lens):
                input_tokens = [int(t) for t in tokens[:-1]]
                target_tokens = tokens[1:]

                all_logprobs = [0.0] * ob_len + logprob
                all_advantages = [0.0] * ob_len + [advantage] * (len(input_tokens) - ob_len)

                if not (len(input_tokens) == len(target_tokens) == len(all_logprobs) == len(all_advantages)):
                    continue

                training_datums.append(
                    types.Datum(
                        model_input=types.ModelInput.from_ints(tokens=input_tokens),
                        loss_fn_inputs={
                            "target_tokens": TensorData.from_torch(torch.tensor(target_tokens)),
                            "logprobs": TensorData.from_torch(torch.tensor(all_logprobs)),
                            "advantages": TensorData.from_torch(torch.tensor(all_advantages)),
                        },
                    )
                )

        if not training_datums:
            print(f"[step {step}] no training datums (all advantages zero or sampling failed)")
            continue

        _ = training_client.forward_backward(training_datums, loss_fn="importance_sampling").result()
        _ = training_client.optim_step(adam_params).result()

        if (step % cfg.save_every) == 0 or step == (n_steps - 1):
            sampler_path = training_client.save_weights_for_sampler(name=f"{step:06d}").result().path
            write_checkpoint_row(log_path, name=f"{step:06d}", sampler_path=sampler_path, step=step)

        reward_mean = (sum(batch_rewards) / len(batch_rewards)) if batch_rewards else 0.0
        print(f"[step {step}] reward_mean={reward_mean:.3f} datums={len(training_datums)} time={time.time()-t0:.1f}s")

    sampler_path = training_client.save_weights_for_sampler(name="final").result().path
    write_checkpoint_row(log_path, name="final", sampler_path=sampler_path, step=n_steps)
    print("Training completed")


if __name__ == "__main__":
    main()
