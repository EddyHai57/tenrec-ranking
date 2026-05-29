import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.training import run_overfit, run_training


def deep_update(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def parse_args():
    parser = argparse.ArgumentParser(description="Train Tenrec CTR torch baselines.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--metadata", help="Override data.metadata_path from config.")
    parser.add_argument("--device", help="Override run.device, e.g. cpu/cuda/auto.")
    parser.add_argument("--model", choices=["lr", "mlp", "deepfm", "dcnv2", "din"], help="Override model.name.")
    parser.add_argument("--seed", type=int, help="Override run.seed.")
    parser.add_argument("--max-train-rows", type=int, help="Smoke-only head row cap.")
    parser.add_argument("--max-valid-rows", type=int, help="Smoke-only head row cap.")
    parser.add_argument("--overfit", action="store_true", help="Run overfit gate instead of normal training.")
    return parser.parse_args()


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def apply_overrides(config: dict, args) -> dict:
    updates = {}
    if args.metadata:
        updates.setdefault("data", {})["metadata_path"] = args.metadata
    if args.device:
        updates.setdefault("run", {})["device"] = args.device
    if args.model:
        updates.setdefault("model", {})["name"] = args.model
    if args.seed is not None:
        updates.setdefault("run", {})["seed"] = args.seed
    if args.max_train_rows is not None:
        updates.setdefault("data", {})["max_train_rows"] = args.max_train_rows
    if args.max_valid_rows is not None:
        updates.setdefault("data", {})["max_valid_rows"] = args.max_valid_rows
    return deep_update(config, updates)


def main():
    args = parse_args()
    config = apply_overrides(load_config(Path(args.config)), args)
    if args.overfit:
        result = run_overfit(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
        return
    result = run_training(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
