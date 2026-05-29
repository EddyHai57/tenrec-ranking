import csv
import hashlib
import json
import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch


def load_metadata(metadata_path: Path) -> dict:
    return json.loads(Path(metadata_path).read_text(encoding="utf-8"))


def encoded_feature_columns(metadata: dict) -> list[str]:
    return [f"{column}_idx" for column in metadata["feature_columns"]]


def raw_feature_columns(metadata: dict) -> list[str]:
    return list(metadata["feature_columns"])


def sequence_feature_specs(metadata: dict) -> dict:
    return dict(metadata.get("sequence_features", {}))


def numeric_feature_names(metadata: dict) -> list[str]:
    return list(metadata.get("numeric_features", {}).get("columns", []))


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
    sequence_features: dict | None = None,
    numeric_features: list[str] | None = None,
):
    path = Path(path)
    labels = []
    features = {column: [] for column in feature_columns}
    sequence_features = sequence_features or {}
    numeric_features = numeric_features or []
    sequences = {name: [] for name in sequence_features}
    numeric_values = []
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
            for name, spec in sequence_features.items():
                sequences[name].append(
                    [int(row[column]) for column in spec["encoded_columns"]]
                )
            if numeric_features:
                numeric_values.append([float(row[column]) for column in numeric_features])
            if len(labels) == batch_size:
                yield make_batch(features, labels, device, sequences, numeric_values)
                labels = []
                features = {column: [] for column in feature_columns}
                sequences = {name: [] for name in sequence_features}
                numeric_values = []
    if labels:
        yield make_batch(features, labels, device, sequences, numeric_values)


def make_batch(
    features: dict[str, list[int]],
    labels: list[float],
    device: torch.device,
    sequence_values: dict[str, list[list[int]]] | None = None,
    numeric_values: list[list[float]] | None = None,
):
    batch = {
        "features": {
            column: torch.tensor(values, dtype=torch.long, device=device)
            for column, values in features.items()
        },
        "labels": torch.tensor(labels, dtype=torch.float32, device=device),
    }
    if sequence_values:
        batch["sequence_features"] = {
            name: torch.tensor(values, dtype=torch.long, device=device)
            for name, values in sequence_values.items()
        }
    if numeric_values:
        batch["numeric_features"] = torch.tensor(
            numeric_values,
            dtype=torch.float32,
            device=device,
        )
    return batch


@dataclass(frozen=True)
class MaterializedTensorTable:
    feature_columns: list[str]
    features: torch.Tensor
    labels: torch.Tensor
    sequence_features: dict = field(default_factory=dict)
    sequences: dict[str, torch.Tensor] = field(default_factory=dict)
    numeric_features: list[str] = field(default_factory=list)
    numeric_values: torch.Tensor | None = None

    @property
    def num_rows(self) -> int:
        return int(self.labels.numel())


def materialized_fieldnames(
    feature_columns: list[str],
    sequence_features: dict | None = None,
    numeric_features: list[str] | None = None,
) -> list[str]:
    sequence_features = sequence_features or {}
    numeric_features = numeric_features or []
    sequence_columns = [
        column
        for spec in sequence_features.values()
        for column in spec["encoded_columns"]
    ]
    return (
        ["click"]
        + [f"{column}_idx" for column in feature_columns]
        + sequence_columns
        + numeric_features
    )


def load_materialized_tensor_table(
    path: Path,
    feature_columns: list[str],
    device: torch.device,
    max_rows: int | None = None,
    sequence_features: dict | None = None,
    numeric_features: list[str] | None = None,
) -> MaterializedTensorTable:
    path = Path(path)
    sequence_features = sequence_features or {}
    numeric_features = numeric_features or []
    expected = materialized_fieldnames(feature_columns, sequence_features, numeric_features)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
    if header is None:
        raise ValueError(f"Missing CSV header: {path}")
    missing = [column for column in expected if column not in header]
    if missing:
        raise ValueError(f"Missing materialized columns in {path}: {missing}")

    usecols = [header.index(column) for column in expected]
    values = np.loadtxt(
        path,
        delimiter=",",
        skiprows=1,
        dtype=np.float32,
        usecols=usecols,
        max_rows=max_rows,
    )
    if values.size == 0:
        raise ValueError(f"No rows were read from {path}")
    if values.ndim == 1:
        values = values.reshape(1, -1)

    labels_np = np.ascontiguousarray(values[:, 0].astype(np.float32))
    feature_end = 1 + len(feature_columns)
    features_np = np.ascontiguousarray(values[:, 1:feature_end].astype(np.int64))
    labels = torch.from_numpy(labels_np).to(device=device)
    features = torch.from_numpy(features_np).to(device=device)
    sequences = {}
    cursor = feature_end
    for name, spec in sequence_features.items():
        width = len(spec["encoded_columns"])
        sequence_np = np.ascontiguousarray(values[:, cursor:cursor + width].astype(np.int64))
        sequences[name] = torch.from_numpy(sequence_np).to(device=device)
        cursor += width
    numeric_values = None
    if numeric_features:
        numeric_np = np.ascontiguousarray(values[:, cursor:cursor + len(numeric_features)])
        numeric_values = torch.from_numpy(numeric_np).to(device=device)
    return MaterializedTensorTable(
        feature_columns=list(feature_columns),
        features=features,
        labels=labels,
        sequence_features=dict(sequence_features),
        sequences=sequences,
        numeric_features=list(numeric_features),
        numeric_values=numeric_values,
    )


def tensor_batch_from_matrix(
    table: MaterializedTensorTable,
    feature_matrix: torch.Tensor,
    labels: torch.Tensor,
    sequence_matrices: dict[str, torch.Tensor] | None = None,
    numeric_matrix: torch.Tensor | None = None,
) -> dict:
    batch = {
        "features": {
            column: feature_matrix[:, index]
            for index, column in enumerate(table.feature_columns)
        },
        "labels": labels,
    }
    if sequence_matrices:
        batch["sequence_features"] = sequence_matrices
    if numeric_matrix is not None:
        batch["numeric_features"] = numeric_matrix
    return batch


def iter_tensor_batches(
    table: MaterializedTensorTable,
    batch_size: int,
    shuffle: bool = False,
    generator: torch.Generator | None = None,
    max_rows: int | None = None,
):
    row_count = table.num_rows if max_rows is None else min(table.num_rows, int(max_rows))
    if row_count <= 0:
        raise ValueError("No tensor rows are available")
    indices = None
    if shuffle:
        indices = torch.randperm(row_count, device=table.features.device, generator=generator)
    for start in range(0, row_count, batch_size):
        end = min(start + batch_size, row_count)
        if indices is None:
            feature_matrix = table.features[start:end]
            labels = table.labels[start:end]
            sequence_matrices = {
                name: values[start:end]
                for name, values in table.sequences.items()
            }
            numeric_matrix = (
                table.numeric_values[start:end]
                if table.numeric_values is not None
                else None
            )
        else:
            batch_indices = indices[start:end]
            feature_matrix = table.features.index_select(0, batch_indices)
            labels = table.labels.index_select(0, batch_indices)
            sequence_matrices = {
                name: values.index_select(0, batch_indices)
                for name, values in table.sequences.items()
            }
            numeric_matrix = (
                table.numeric_values.index_select(0, batch_indices)
                if table.numeric_values is not None
                else None
            )
        yield tensor_batch_from_matrix(
            table,
            feature_matrix,
            labels,
            sequence_matrices,
            numeric_matrix,
        )


def load_first_batches(
    path: Path,
    feature_columns: list[str],
    batch_size: int,
    num_batches: int,
    device: torch.device,
    sequence_features: dict | None = None,
    numeric_features: list[str] | None = None,
) -> list[dict]:
    batches = []
    for batch in iter_materialized_batches(
        path=path,
        feature_columns=feature_columns,
        batch_size=batch_size,
        device=device,
        max_rows=batch_size * num_batches,
        sequence_features=sequence_features,
        numeric_features=numeric_features,
    ):
        batches.append(batch)
        if len(batches) >= num_batches:
            break
    if len(batches) != num_batches:
        raise ValueError(f"Expected {num_batches} batches but got {len(batches)}")
    return batches
