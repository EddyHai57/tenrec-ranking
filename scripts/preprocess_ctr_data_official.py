import argparse
import csv
import hashlib
import json
import random
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.data import RESERVED_MISSING_INDEX, RESERVED_OOV_INDEX
from tenrec.torch_data import create_hash_bucket_shuffle


PREPROCESSING_VERSION = "official_compatible_v0.1"
SPLITS = ("train", "valid", "test")


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def make_run_id(config: dict) -> str:
    digest = hashlib.sha1(canonical_json(config).encode("utf-8")).hexdigest()[:12]
    return f"ctr-{digest}-official"


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_split_paths(metadata: dict) -> list[Path]:
    return [Path(metadata["pass2"]["split_paths"][split]) for split in SPLITS]


def count_labels(paths: list[Path], max_input_rows: int | None = None) -> Counter:
    counts = Counter()
    seen_rows = 0
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if max_input_rows is not None and seen_rows >= max_input_rows:
                    return counts
                seen_rows += 1
                counts[row["click"]] += 1
    return counts


def iter_source_rows(paths: list[Path], max_input_rows: int | None = None):
    seen_rows = 0
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if max_input_rows is not None and seen_rows >= max_input_rows:
                    return
                seen_rows += 1
                yield row


def materialized_fieldnames(feature_columns: list[str]) -> list[str]:
    return ["click"] + [f"{column}_idx" for column in feature_columns]


def write_sampled_rows(
    source_paths: list[Path],
    sampled_path: Path,
    fieldnames: list[str],
    seed: int,
    negative_keep_probability: float,
    max_input_rows: int | None,
) -> dict:
    rng = random.Random(seed)
    counts = Counter()
    scanned_rows = 0
    sampled_path.parent.mkdir(parents=True, exist_ok=True)
    with sampled_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in iter_source_rows(source_paths, max_input_rows=max_input_rows):
            scanned_rows += 1
            label = row["click"]
            keep = label == "1" or rng.random() < negative_keep_probability
            if not keep:
                continue
            writer.writerow({field: row[field] for field in fieldnames})
            counts[label] += 1
    return {
        "scanned_rows": scanned_rows,
        "sampled_rows": sum(counts.values()),
        "sample_label_counts": dict(counts),
        "negative_keep_probability": negative_keep_probability,
    }


def split_shuffled_rows(
    shuffled_path: Path,
    materialized_dir: Path,
    fieldnames: list[str],
    train_ratio: float,
    valid_ratio: float,
    test_ratio: float,
) -> dict:
    total_rows = 0
    with shuffled_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for _ in reader:
            total_rows += 1

    train_rows = int(total_rows * train_ratio)
    valid_rows = int(total_rows * valid_ratio)
    test_rows = total_rows - train_rows - valid_rows
    split_limits = {
        "train": train_rows,
        "valid": valid_rows,
        "test": test_rows,
    }
    materialized_dir.mkdir(parents=True, exist_ok=True)
    split_paths = {split: materialized_dir / f"{split}.csv" for split in SPLITS}
    handles = {
        split: split_paths[split].open("w", encoding="utf-8", newline="")
        for split in SPLITS
    }
    writers = {split: csv.DictWriter(handles[split], fieldnames=fieldnames) for split in SPLITS}
    for writer in writers.values():
        writer.writeheader()

    split_rows = Counter()
    label_counts = {split: Counter() for split in SPLITS}
    distinct_groups = {split: set() for split in SPLITS}
    try:
        with shuffled_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            current_split_index = 0
            for row in reader:
                while split_rows[SPLITS[current_split_index]] >= split_limits[SPLITS[current_split_index]]:
                    current_split_index += 1
                split = SPLITS[current_split_index]
                writers[split].writerow(row)
                split_rows[split] += 1
                label_counts[split][row["click"]] += 1
                distinct_groups[split].add(row["user_id_idx"])
    finally:
        for handle in handles.values():
            handle.close()

    return {
        "split_paths": {split: str(path) for split, path in split_paths.items()},
        "split_rows": dict(split_rows),
        "label_counts": {split: dict(counts) for split, counts in label_counts.items()},
        "distinct_group_counts": {
            split: len(groups) for split, groups in distinct_groups.items()
        },
    }


def preprocess_official_compatible(
    source_metadata_path: Path,
    output_root: Path,
    seed: int,
    neg_sampling_ratio: int = 2,
    train_ratio: float = 0.8,
    valid_ratio: float = 0.1,
    test_ratio: float = 0.1,
    shuffle_bucket_count: int = 64,
    max_input_rows: int | None = None,
    overwrite: bool = False,
) -> dict:
    source_metadata_path = Path(source_metadata_path)
    output_root = Path(output_root)
    source_metadata = load_json(source_metadata_path)
    source_paths = source_split_paths(source_metadata)
    feature_columns = list(source_metadata["feature_columns"])
    fieldnames = materialized_fieldnames(feature_columns)

    config = {
        "protocol": "official-compatible",
        "source_metadata_path": str(source_metadata_path),
        "source_run_id": source_metadata["run_id"],
        "seed": seed,
        "neg_sampling_ratio": neg_sampling_ratio,
        "split_rule": "random_8_1_1",
        "train_ratio": train_ratio,
        "valid_ratio": valid_ratio,
        "test_ratio": test_ratio,
        "shuffle_bucket_count": shuffle_bucket_count,
        "max_input_rows": max_input_rows,
        "vocab_source": f"{source_metadata['run_id']} (reuse)",
        "drop_sequence_features": True,
    }
    run_id = make_run_id(config)
    run_dir = output_root / run_id
    if run_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Official preprocessing run already exists: {run_dir}")
        shutil.rmtree(run_dir)
    tmp_dir = run_dir / "tmp"
    materialized_dir = run_dir / "materialized"
    sampled_path = tmp_dir / "sampled.csv"
    shuffled_path = tmp_dir / "sampled_shuffled.csv"

    started_at = time.time()
    source_label_counts = count_labels(source_paths, max_input_rows=max_input_rows)
    positive_count = int(source_label_counts.get("1", 0))
    negative_count = int(source_label_counts.get("0", 0))
    if positive_count <= 0 or negative_count <= 0:
        raise ValueError("official-compatible sampling requires both positive and negative rows")
    target_negative_count = min(negative_count, positive_count * int(neg_sampling_ratio))
    negative_keep_probability = target_negative_count / negative_count

    sample_summary = write_sampled_rows(
        source_paths=source_paths,
        sampled_path=sampled_path,
        fieldnames=fieldnames,
        seed=seed,
        negative_keep_probability=negative_keep_probability,
        max_input_rows=max_input_rows,
    )
    create_hash_bucket_shuffle(
        input_path=sampled_path,
        output_path=shuffled_path,
        seed=seed,
        bucket_count=shuffle_bucket_count,
    )
    pass2_summary = split_shuffled_rows(
        shuffled_path=shuffled_path,
        materialized_dir=materialized_dir,
        fieldnames=fieldnames,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
        test_ratio=test_ratio,
    )
    pass2_summary["elapsed_seconds"] = round(time.time() - started_at, 3)
    shutil.rmtree(tmp_dir)

    train_counts = pass2_summary["label_counts"]["train"]
    train_positive = int(train_counts.get("1", 0))
    train_rows = int(pass2_summary["split_rows"]["train"])
    metadata = {
        "run_id": run_id,
        "protocol": "official-compatible",
        "data_contract_version": source_metadata.get("data_contract_version"),
        "preprocessing_version": PREPROCESSING_VERSION,
        "git_commit": git_commit(),
        "source_metadata_path": str(source_metadata_path),
        "source_run_id": source_metadata["run_id"],
        "config": config,
        "reserved_indices": source_metadata.get(
            "reserved_indices",
            {
                "oov": RESERVED_OOV_INDEX,
                "missing": RESERVED_MISSING_INDEX,
                "seen_values_start": 2,
            },
        ),
        "split_rule": {
            "description": "Official-compatible 1:2 negative sampling, global hash-bucket shuffle, random 8:1:1 split.",
            "shuffle": True,
            "deduplicate": False,
            "seed_used_by_split": True,
            "rule": "random_8_1_1",
        },
        "feature_columns": feature_columns,
        "sequence_features": {},
        "label_column": source_metadata.get("label_column", "click"),
        "group_column": source_metadata.get("group_column", "user_id"),
        "vocab_sizes": dict(source_metadata["vocab_sizes"]),
        "vocab_paths": dict(source_metadata["vocab_paths"]),
        "official": {
            "neg_sampling_ratio": neg_sampling_ratio,
            "split_rule": "random_8_1_1",
            "vocab_source": f"{source_metadata['run_id']} (reuse)",
            "source_label_counts": dict(source_label_counts),
            "target_negative_count": target_negative_count,
            "sample_label_counts": sample_summary["sample_label_counts"],
            "sampled_rows": sample_summary["sampled_rows"],
            "negative_keep_probability": negative_keep_probability,
            "train_base_rate": train_positive / train_rows if train_rows else None,
        },
        "pass1": {
            "source_total_rows": sum(source_label_counts.values()),
            "source_label_counts": dict(source_label_counts),
            "vocab_source": f"{source_metadata['run_id']} (reuse)",
            "build_vocab": False,
        },
        "pass2": pass2_summary,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def parse_args():
    parser = argparse.ArgumentParser(description="Official-compatible Tenrec CTR preprocessing.")
    parser.add_argument("--config")
    parser.add_argument("--source-metadata")
    parser.add_argument("--output-root", default="outputs/preprocessed")
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--neg-sampling-ratio", type=int, default=2)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--shuffle-bucket-count", type=int, default=64)
    parser.add_argument("--max-input-rows", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_cli_config(args) -> dict:
    config = {}
    if args.config:
        with Path(args.config).open("r", encoding="utf-8") as handle:
            config.update(yaml.safe_load(handle) or {})
    if args.source_metadata:
        config["source_metadata_path"] = args.source_metadata
    config.setdefault("output_root", args.output_root)
    config.setdefault("seed", args.seed)
    config.setdefault("neg_sampling_ratio", args.neg_sampling_ratio)
    config.setdefault("train_ratio", args.train_ratio)
    config.setdefault("valid_ratio", args.valid_ratio)
    config.setdefault("test_ratio", args.test_ratio)
    config.setdefault("shuffle_bucket_count", args.shuffle_bucket_count)
    if args.max_input_rows is not None:
        config["max_input_rows"] = args.max_input_rows
    if args.overwrite:
        config["overwrite"] = True
    if "source_metadata_path" not in config:
        raise SystemExit("--source-metadata or --config with source_metadata_path is required")
    return config


def main():
    args = parse_args()
    config = load_cli_config(args)
    metadata = preprocess_official_compatible(
        source_metadata_path=Path(config["source_metadata_path"]),
        output_root=Path(config["output_root"]),
        seed=int(config["seed"]),
        neg_sampling_ratio=int(config["neg_sampling_ratio"]),
        train_ratio=float(config["train_ratio"]),
        valid_ratio=float(config["valid_ratio"]),
        test_ratio=float(config["test_ratio"]),
        shuffle_bucket_count=int(config["shuffle_bucket_count"]),
        max_input_rows=config.get("max_input_rows"),
        overwrite=bool(config.get("overwrite", False)),
    )
    print(
        json.dumps(
            {
                "run_id": metadata["run_id"],
                "metadata_path": str(Path(metadata["pass2"]["split_paths"]["train"]).parents[1] / "metadata.json"),
                "protocol": metadata["protocol"],
                "split_rows": metadata["pass2"]["split_rows"],
                "label_counts": metadata["pass2"]["label_counts"],
                "official": metadata["official"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
