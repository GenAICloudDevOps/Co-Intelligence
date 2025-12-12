#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> None:
    dataset_path = os.getenv("DATASET_PATH")
    if not dataset_path:
        raise SystemExit("DATASET_PATH is required")

    path = Path(dataset_path).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}")

    total = 0
    bad = 0
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                bad += 1
                print(f"[line {line_no}] invalid JSON: {exc}")
                continue

            messages = obj.get("messages")
            if not isinstance(messages, list) or not messages:
                bad += 1
                print(f"[line {line_no}] missing/invalid 'messages'")
                continue
            for mi, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    bad += 1
                    print(f"[line {line_no}] messages[{mi}] not an object")
                    break
                if msg.get("role") not in {"system", "user", "assistant", "tool"}:
                    bad += 1
                    print(f"[line {line_no}] messages[{mi}] invalid role: {msg.get('role')}")
                    break
                if not isinstance(msg.get("content"), str):
                    bad += 1
                    print(f"[line {line_no}] messages[{mi}] missing string 'content'")
                    break

    print("====================================")
    print(f"Dataset: {path}")
    print(f"Rows: {total}")
    print(f"Invalid rows: {bad}")
    if bad:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

