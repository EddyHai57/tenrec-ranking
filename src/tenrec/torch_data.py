import csv
import hashlib
import json
import random
import shutil
from pathlib import Path

import torch


def load_metadata(metadata_path: Path) -> dict:
    return json.loads(Path(metadata_path).read_text(encoding="utf-8"))


def encoded_feature_columns(metadata: dict) -> list[str]:
    return [f"{column}_idx" for column in metadata["feature_columns"]]


def raw_feature_columns(metadata: dict) -> list[str]:
    return list(metadata["feature_columns"])


def split_path(metadata: dict, split: str) -> Path:
    return Path(metadata["pass2"]["split_paths"][split])


def shuffled_train_path(metadata_path: Path, seed: int, bucket_count: int) -> Path:
    metadata_path = Path(metadata_path)
    return (
        metadata_path.parent
        / "materialized"
        / f"train_shuffled_seed{seed}_b{bucket_count}.csv"
    )


def row_shuffle_bucket(row: dict, line_no: int, seed: int, bucket_count: int) -> int:
    payload = "|".join([str(seed), str(line_no)] + [row[key] for key in sorted(row)])
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % bucket_count


def create_hash_bucket_shuffle(
    input_path: Path,
    output_path: Path,
    seed: int,
    bucket_count: int,
) -> Path:
    """Create a deterministic materialized shuffle file without keeping all rows in memory."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_path.parent / f".shuffle_tmp_seed{seed}_b{bucket_count}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    bucket_handles = []
    bucket_writers = []
    try:
        with input_path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise ValueError(f"Missing CSV header: {input_path}")
            fieldnames = list(reader.fieldnames)
            for bucket_id in range(bucket_count):
                handle = (tmp_dir / f"bucket_{bucket_id:05d}.csv").open(
                    "w", encoding="utf-8", newline=""
                )
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                bucket_handles.append(handle)
                bucket_writers.append(writer)
            for line_no, row in enumerate(reader):
                bucket_id = row_shuffle_bucket(row, line_no, seed, bucket_count)
                bucket_writers[bucket_id].writerow(row)
    finally:
        for handle in bucket_handles:
            handle.close()

    bucket_order = list(range(bucket_count))
    random.Random(seed).shuffle(bucket_order)
    with output_path.open("w", encoding="utf-8", newline="") as target:
        writer = None
        for bucket_id in bucket_order:
            bucket_path = tmp_dir / f"bucket_{bucket_id:05d}.csv"
            with bucket_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if writer is None:
                    writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
                    writer.writeheader()
                rows = list(reader)
                random.Random(seed + bucket_id).shuffle(rows)
                for row in rows:
                    writer.writerow(row)

    shutil.rmtree(tmp_dir)
    return output_path


def ensure_shuffled_train(metadata_path: Path, seed: int, bucket_count: int) -> Path:
    metadata = load_metadata(metadata_path)
    output_path = shuffled_train_path(metadata_path, seed, bucket_count)
    if output_path.exists():
        return output_path
    return create_hash_bucket_shuffle(
        input_path=split_path(metadata, "train"),
        output_path=output_path,
        seed=seed,
        bucket_count=bucket_count,
    )


def iter_materialized_batches(
    path: Path,
    feature_columns: list[str],
    batch_size: int,
    device: torch.device,
    max_rows: int | None = None,
):
    path = Path(path)
    labels = []
    features = {column: [] for column in feature_columns}
    seen_rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if max_rows is not None and seen_rows >= max_rows:
                break
            seen_rows += 1
            labels.append(float(row["click"]))
            for column in feature_columns:
                features[column].append(int(row[f"{column}_idx"]))
            if len(labels) == batch_size:
                yield make_batch(features, labels, device)
                labels = []
                features = {column: [] for column in feature_columns}
    if labels:
        yield make_batch(features, labels, device)


def make_batch(features: dict[str, list[int]], labels: list[float], device: torch.device):
    return {
        "features": {
            column: torch.tensor(values, dtype=torch.long, device=device)
            for column, values in features.items()
        },
        "labels": torch.tensor(labels, dtype=torch.float32, device=device),
    }


def load_first_batches(
    path: Path,
    feature_columns: list[str],
    batch_size: int,
    num_batches: int,
    device: torch.device,
) -> list[dict]:
    batches = []
    for batch in iter_materialized_batches(
        path=path,
        feature_columns=feature_columns,
        batch_size=batch_size,
        device=device,
        max_rows=batch_size * num_batches,
    ):
        batches.append(batch)
        if len(batches) >= num_batches:
            break
    if len(batches) != num_batches:
        raise ValueError(f"Expected {num_batches} batches but got {len(batches)}")
    return batches
