#!/usr/bin/env python3
"""Merge Firebase web config JSON into the app .env file."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: apply-firebase-env.py <config.json> <app_dir>", file=sys.stderr)
        return 1

    config_path = Path(sys.argv[1])
    app_dir = Path(sys.argv[2])
    env_path = app_dir / ".env"

    config = json.loads(config_path.read_text(encoding="utf-8"))
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    keys = set(config.keys())
    kept = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0]
            if key in keys:
                continue
        kept.append(line)

    for key, value in config.items():
        kept.append(f"{key}={value}")

    env_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    print(f"Updated {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
