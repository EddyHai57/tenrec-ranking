import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


NUMERIC_COLUMNS = [
    "item_hist_ctr",
    "user_hist_ctr",
    "user_log_impressions",
    "item_log_impressions",
    "category_hist_ctr",
    "user_category_hist_ctr",
]


@dataclass
class Counts:
    clicks: float = 0.0
    impressions: float = 0.0

    def add(self, label: float) -> None:
        self.clicks += label
        self.impressions += 1.0

    def subtract(self, other: "Counts") -> "Counts":
        return Counts(
            clicks=self.clicks - other.clicks,
            impressions=self.impressions - other.impressions,
        )


class CountTable:
    def __init__(self):
        self.counts: dict[object, Counts] = {}

    def add(self, key, label: float) -> None:
        self.counts.setdefault(key, Counts()).add(label)

    def get(self, key) -> Counts:
        return self.counts.get(key, Counts())

    def subtract(self, other: "CountTable") -> "CountTable":
        result = CountTable()
        for key, value in self.counts.items():
            result.counts[key] = value.subtract(other.get(key))
        return result


@dataclass
class RunningStats:
    count: int = 0
    sums: dict[str, float] | None = None
    sum_squares: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if self.sums is None:
            self.sums = {column: 0.0 for column in NUMERIC_COLUMNS}
        if self.sum_squares is None:
            self.sum_squares = {column: 0.0 for column in NUMERIC_COLUMNS}

    def add(self, values: dict[str, float]) -> None:
        self.count += 1
        for column in NUMERIC_COLUMNS:
            value = values[column]
            self.sums[column] += value
            self.sum_squares[column] += value * value

    def finalize(self) -> dict[str, dict[str, float]]:
        if self.count <= 0:
            raise ValueError("Cannot standardize empty train features")
        stats = {}
        for column in NUMERIC_COLUMNS:
            mean = self.sums[column] / self.count
            variance = max(self.sum_squares[column] / self.count - mean * mean, 0.0)
            std = math.sqrt(variance)
            stats[column] = {"mean": mean, "std": std if std > 1e-12 else 1.0}
        return stats


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


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_run_id(config: dict) -> str:
    digest = hashlib.sha1(canonical_json(config).encode("utf-8")).hexdigest()[:12]
    return f"ctr-{digest}-stats"


def load_metadata(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_header(path: Path) -> list[str]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader.fieldnames)


def iter_rows(path: Path):
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        for row in reader:
            yield row


def smoothed_ctr(clicks: float, impressions: float, global_ctr: float, alpha: float) -> float:
    return (clicks + alpha * global_ctr) / (impressions + alpha)


def build_count_table(rows: list[dict], key_fn) -> CountTable:
    table = CountTable()
    for row in rows:
        table.add(key_fn(row), float(row["click"]))
    return table


def empty_key_tables() -> dict[str, CountTable]:
    return {
        "item": CountTable(),
        "user": CountTable(),
        "category": CountTable(),
        "user_category": CountTable(),
    }


def add_row_to_key_tables(tables: dict[str, CountTable], row: dict, label: float) -> None:
    tables["item"].add(row["item_id_idx"], label)
    tables["user"].add(row["user_id_idx"], label)
    tables["category"].add(row["video_category_idx"], label)
    tables["user_category"].add((row["user_id_idx"], row["video_category_idx"]), label)


def stable_fold(row: dict, row_index: int, seed: int, folds: int) -> int:
    payload = "|".join([str(seed), str(row_index), row["user_id_idx"], row["item_id_idx"]])
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % folds


def key_tables(rows: list[dict]) -> dict[str, CountTable]:
    return {
        "item": build_count_table(rows, lambda row: row["item_id_idx"]),
        "user": build_count_table(rows, lambda row: row["user_id_idx"]),
        "category": build_count_table(rows, lambda row: row["video_category_idx"]),
        "user_category": build_count_table(
            rows, lambda row: (row["user_id_idx"], row["video_category_idx"])
        ),
    }


def maybe_exclude_fold(counts: Counts, fold_counts: Counts | None) -> Counts:
    if fold_counts is None:
        return counts
    return counts.subtract(fold_counts)


def raw_feature_values(
    row: dict,
    tables: dict[str, CountTable],
    global_ctr: float,
    alpha: float,
    excluded_tables: dict[str, CountTable] | None = None,
) -> tuple[dict, dict]:
    item_counts = tables["item"].get(row["item_id_idx"])
    user_counts = tables["user"].get(row["user_id_idx"])
    category_counts = tables["category"].get(row["video_category_idx"])
    user_category_counts = tables["user_category"].get(
        (row["user_id_idx"], row["video_category_idx"])
    )
    if excluded_tables is not None:
        item_counts = maybe_exclude_fold(
            item_counts,
            excluded_tables["item"].get(row["item_id_idx"]),
        )
        user_counts = maybe_exclude_fold(
            user_counts,
            excluded_tables["user"].get(row["user_id_idx"]),
        )
        category_counts = maybe_exclude_fold(
            category_counts,
            excluded_tables["category"].get(row["video_category_idx"]),
        )
        user_category_counts = maybe_exclude_fold(
            user_category_counts,
            excluded_tables["user_category"].get(
                (row["user_id_idx"], row["video_category_idx"])
            ),
        )
    values = {
        "item_hist_ctr": smoothed_ctr(item_counts.clicks, item_counts.impressions, global_ctr, alpha),
        "user_hist_ctr": smoothed_ctr(user_counts.clicks, user_counts.impressions, global_ctr, alpha),
        "user_log_impressions": math.log1p(user_counts.impressions),
        "item_log_impressions": math.log1p(item_counts.impressions),
        "category_hist_ctr": smoothed_ctr(category_counts.clicks, category_counts.impressions, global_ctr, alpha),
        "user_category_hist_ctr": smoothed_ctr(
            user_category_counts.clicks,
            user_category_counts.impressions,
            global_ctr,
            alpha,
        ),
    }
    missing = {
        "item_hist_ctr": item_counts.impressions == 0,
        "user_hist_ctr": user_counts.impressions == 0,
        "user_log_impressions": user_counts.impressions == 0,
        "item_log_impressions": item_counts.impressions == 0,
        "category_hist_ctr": category_counts.impressions == 0,
        "user_category_hist_ctr": user_category_counts.impressions == 0,
    }
    return values, missing


def standardization_stats(raw_rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    stats = {}
    for column in NUMERIC_COLUMNS:
        values = [row[column] for row in raw_rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        std = math.sqrt(variance)
        stats[column] = {"mean": mean, "std": std if std > 1e-12 else 1.0}
    return stats


def transform_values(values: dict[str, float], stats: dict[str, dict[str, float]]) -> dict[str, str]:
    transformed = {}
    for column in NUMERIC_COLUMNS:
        mean = stats[column]["mean"]
        std = stats[column]["std"]
        transformed[column] = f"{(values[column] - mean) / std:.8g}"
    return transformed


def label_counts(rows: list[dict]) -> dict[str, int]:
    result = {"0": 0, "1": 0}
    for row in rows:
        result[str(int(float(row["click"])))] += 1
    return {key: value for key, value in result.items() if value}


def empty_label_counts() -> dict[str, int]:
    return {"0": 0, "1": 0}


def add_label_count(counts: dict[str, int], label: float) -> None:
    counts[str(int(label))] += 1


def finalize_label_counts(counts: dict[str, int]) -> dict[str, int]:
    return {key: value for key, value in counts.items() if value}


def scan_train_counts(
    train_path: Path,
    folds: int,
    seed: int,
) -> tuple[dict[str, CountTable], dict[int, dict[str, CountTable]], dict[str, int], int, float]:
    full_tables = empty_key_tables()
    fold_tables = {fold: empty_key_tables() for fold in range(folds)}
    counts = empty_label_counts()
    rows = 0
    clicks = 0.0
    for index, row in enumerate(iter_rows(train_path)):
        label = float(row["click"])
        rows += 1
        clicks += label
        add_label_count(counts, label)
        add_row_to_key_tables(full_tables, row, label)
        fold = stable_fold(row, index, seed, folds)
        add_row_to_key_tables(fold_tables[fold], row, label)
    if rows <= 0:
        raise ValueError(f"No train rows were read from {train_path}")
    return full_tables, fold_tables, finalize_label_counts(counts), rows, clicks / rows


def feature_tables_for_train_row(
    row: dict,
    row_index: int,
    mode: str,
    seed: int,
    folds: int,
    full_tables: dict[str, CountTable],
    fold_tables: dict[int, dict[str, CountTable]],
) -> dict[str, CountTable] | None:
    if mode == "naive":
        return None
    fold = stable_fold(row, row_index, seed, folds)
    return fold_tables[fold]


def compute_train_standardization(
    train_path: Path,
    full_tables: dict[str, CountTable],
    fold_tables: dict[int, dict[str, CountTable]],
    global_ctr: float,
    alpha: float,
    folds: int,
    seed: int,
    mode: str,
) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
    running = RunningStats()
    missing_counts = {column: 0 for column in NUMERIC_COLUMNS}
    for index, row in enumerate(iter_rows(train_path)):
        excluded_tables = feature_tables_for_train_row(
            row=row,
            row_index=index,
            mode=mode,
            seed=seed,
            folds=folds,
            full_tables=full_tables,
            fold_tables=fold_tables,
        )
        values, missing = raw_feature_values(
            row=row,
            tables=full_tables,
            global_ctr=global_ctr,
            alpha=alpha,
            excluded_tables=excluded_tables,
        )
        running.add(values)
        for column, is_missing in missing.items():
            missing_counts[column] += int(is_missing)
    return running.finalize(), missing_counts


def write_transformed_split(
    split: str,
    input_path: Path,
    output_path: Path,
    output_header: list[str],
    full_tables: dict[str, CountTable],
    fold_tables: dict[int, dict[str, CountTable]],
    global_ctr: float,
    alpha: float,
    folds: int,
    seed: int,
    mode: str,
    stats: dict[str, dict[str, float]],
) -> tuple[int, dict[str, int], dict[str, int]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    label_counts_by_split = empty_label_counts()
    missing_counts = {column: 0 for column in NUMERIC_COLUMNS}
    rows = 0
    with Path(output_path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_header)
        writer.writeheader()
        for index, row in enumerate(iter_rows(input_path)):
            label = float(row["click"])
            rows += 1
            add_label_count(label_counts_by_split, label)
            excluded_tables = None
            if split == "train":
                excluded_tables = feature_tables_for_train_row(
                    row=row,
                    row_index=index,
                    mode=mode,
                    seed=seed,
                    folds=folds,
                    full_tables=full_tables,
                    fold_tables=fold_tables,
                )
            values, missing = raw_feature_values(
                row=row,
                tables=full_tables,
                global_ctr=global_ctr,
                alpha=alpha,
                excluded_tables=excluded_tables,
            )
            for column, is_missing in missing.items():
                missing_counts[column] += int(is_missing)
            writer.writerow({**row, **transform_values(values, stats)})
    if rows <= 0:
        raise ValueError(f"No {split} rows were read from {input_path}")
    return rows, finalize_label_counts(label_counts_by_split), missing_counts


def preprocess_stats_features(
    source_metadata_path: Path,
    output_root: Path,
    alpha: float = 20.0,
    folds: int = 5,
    seed: int = 20260525,
    mode: str = "oof",
    overwrite: bool = False,
) -> dict:
    if mode not in {"oof", "naive"}:
        raise ValueError("mode must be 'oof' or 'naive'")
    if folds < 2:
        raise ValueError("folds must be >= 2")
    source_metadata_path = Path(source_metadata_path)
    output_root = Path(output_root)
    source_metadata = load_metadata(source_metadata_path)
    config = {
        "source_run_id": source_metadata["run_id"],
        "source_metadata_path": str(source_metadata_path),
        "alpha": alpha,
        "folds": folds,
        "seed": seed,
        "mode": mode,
        "numeric_columns": NUMERIC_COLUMNS,
    }
    run_id = make_run_id(config)
    run_dir = output_root / run_id
    if run_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Stats run already exists: {run_dir}")
        shutil.rmtree(run_dir)
    materialized_dir = run_dir / "materialized"

    split_paths = {
        split: Path(source_metadata["pass2"]["split_paths"][split])
        for split in ("train", "valid", "test")
    }
    header = read_header(split_paths["train"])
    full_tables, fold_tables, train_label_counts, train_rows, global_ctr = scan_train_counts(
        train_path=split_paths["train"],
        folds=folds,
        seed=seed,
    )
    stats, train_missing_counts = compute_train_standardization(
        train_path=split_paths["train"],
        full_tables=full_tables,
        fold_tables=fold_tables,
        global_ctr=global_ctr,
        alpha=alpha,
        folds=folds,
        seed=seed,
        mode=mode,
    )
    output_header = header + NUMERIC_COLUMNS
    new_split_paths = {}
    rows_by_split = {}
    label_counts_by_split = {}
    raw_missing_counts = {}
    for split in ("train", "valid", "test"):
        path = materialized_dir / f"{split}.csv"
        rows, split_label_counts, missing_counts = write_transformed_split(
            split=split,
            input_path=split_paths[split],
            output_path=path,
            output_header=output_header,
            full_tables=full_tables,
            fold_tables=fold_tables,
            global_ctr=global_ctr,
            alpha=alpha,
            folds=folds,
            seed=seed,
            mode=mode,
            stats=stats,
        )
        new_split_paths[split] = str(path)
        rows_by_split[split] = rows
        label_counts_by_split[split] = split_label_counts
        raw_missing_counts[split] = missing_counts
    if rows_by_split["train"] != train_rows:
        raise ValueError("Train row count changed between count and write passes")
    if label_counts_by_split["train"] != train_label_counts:
        raise ValueError("Train label counts changed between count and write passes")
    if raw_missing_counts["train"] != train_missing_counts:
        raise ValueError("Train missing counts changed between stats and write passes")
    metadata = dict(source_metadata)
    metadata.update(
        {
            "run_id": run_id,
            "source_run_id": source_metadata["run_id"],
            "source_metadata_path": str(source_metadata_path),
            "preprocessing_version": "stats_features_streaming_v0.2",
            "git_commit": git_commit(),
            "numeric_features": {
                "columns": list(NUMERIC_COLUMNS),
                "alpha": alpha,
                "folds": folds,
                "mode": mode,
                "implementation": "streaming_fold_out",
                "standardization": stats,
                "lookup_scope": {
                    "train": "5fold_oof" if mode == "oof" else "naive_in_sample",
                    "valid": "train_only",
                    "test": "train_only",
                },
                "missing_rates": {
                    split: {
                        column: raw_missing_counts[split][column] / rows_by_split[split]
                        for column in NUMERIC_COLUMNS
                    }
                    for split in ("train", "valid", "test")
                },
            },
            "pass2": {
                **source_metadata["pass2"],
                "split_paths": new_split_paths,
                "split_rows": rows_by_split,
                "label_counts": label_counts_by_split,
            },
        }
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def parse_args():
    parser = argparse.ArgumentParser(description="Add leakage-safe statistical numeric features.")
    parser.add_argument("--source-metadata", required=True)
    parser.add_argument("--output-root", default="outputs/preprocessed")
    parser.add_argument("--alpha", type=float, default=20.0)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--mode", choices=["oof", "naive"], default="oof")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    started = time.time()
    metadata = preprocess_stats_features(
        source_metadata_path=Path(args.source_metadata),
        output_root=Path(args.output_root),
        alpha=args.alpha,
        folds=args.folds,
        seed=args.seed,
        mode=args.mode,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            {
                "run_id": metadata["run_id"],
                "metadata_path": str(Path(metadata["pass2"]["split_paths"]["train"]).parents[1] / "metadata.json"),
                "source_run_id": metadata["source_run_id"],
                "mode": metadata["numeric_features"]["mode"],
                "numeric_features": metadata["numeric_features"]["columns"],
                "split_rows": metadata["pass2"]["split_rows"],
                "elapsed_seconds": round(time.time() - started, 3),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
