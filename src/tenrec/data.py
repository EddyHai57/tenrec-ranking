import csv
import hashlib
import json
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


DATA_CONTRACT_VERSION = "ctr_mvp_v0.1"
PREPROCESSING_VERSION = "two_pass_v0.1"
SPLITS = ("train", "valid", "test")
RESERVED_OOV_INDEX = 0
RESERVED_MISSING_INDEX = 1
RESERVED_TOKENS = {
    "__OOV__": RESERVED_OOV_INDEX,
    "__MISSING__": RESERVED_MISSING_INDEX,
}
DEFAULT_MISSING_VALUES = {"", "\\N"}


@dataclass(frozen=True)
class SplitCounts:
    train: int
    valid: int
    test: int


def split_counts_for_user(row_count: int) -> SplitCounts:
    """Deterministic user-internal 80/10/10 split used by the MVP contract."""
    if row_count < 0:
        raise ValueError("row_count must be non-negative")
    if row_count < 3:
        return SplitCounts(train=row_count, valid=0, test=0)
    valid_count = max(1, int(row_count * 0.1))
    test_count = max(1, int(row_count * 0.1))
    train_count = row_count - valid_count - test_count
    return SplitCounts(train=train_count, valid=valid_count, test=test_count)


def split_names_for_user(row_count: int) -> list[str]:
    counts = split_counts_for_user(row_count)
    return (
        ["train"] * counts.train
        + ["valid"] * counts.valid
        + ["test"] * counts.test
    )


def iter_user_blocks(input_path: Path):
    input_path = Path(input_path)
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        current_user = None
        current_rows = []
        for row in reader:
            user_id = row["user_id"]
            if current_user is None:
                current_user = user_id
            if user_id != current_user:
                yield current_user, current_rows
                current_user = user_id
                current_rows = []
            current_rows.append(row)
        if current_rows:
            yield current_user, current_rows


def normalize_missing_values(values) -> set[str]:
    if values is None:
        return set(DEFAULT_MISSING_VALUES)
    return {str(value) for value in values}


def is_missing_value(value: str, missing_values: set[str]) -> bool:
    return value in missing_values


def empty_vocab() -> dict[str, int]:
    return dict(RESERVED_TOKENS)


def add_to_vocab(vocab: dict[str, int], value: str, missing_values: set[str]) -> None:
    if is_missing_value(value, missing_values):
        return
    if value not in vocab:
        vocab[value] = len(vocab)


def encode_value(vocab: dict[str, int], value: str, missing_values: set[str]) -> int:
    if is_missing_value(value, missing_values):
        return RESERVED_MISSING_INDEX
    return vocab.get(value, RESERVED_OOV_INDEX)


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_size_bytes(path: Path) -> int:
    return Path(path).stat().st_size


def make_run_id(input_path: Path, config: dict) -> str:
    payload = {
        "data_contract_version": DATA_CONTRACT_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "input_name": Path(input_path).name,
        "input_size_bytes": file_size_bytes(input_path),
        "config": config,
    }
    digest = hashlib.sha1(canonical_json(payload).encode("utf-8")).hexdigest()[:12]
    return f"ctr-{digest}"


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


def build_train_vocabs(
    input_path: Path,
    feature_columns: list[str],
    missing_values: dict[str, set[str]],
) -> tuple[dict[str, dict[str, int]], dict]:
    vocabs = {column: empty_vocab() for column in feature_columns}
    split_rows = Counter()
    short_user_counts = Counter()
    user_blocks = 0
    total_rows = 0

    for _, rows in iter_user_blocks(input_path):
        user_blocks += 1
        total_rows += len(rows)
        short_user_counts[str(len(rows)) if len(rows) < 3 else ">=3"] += 1
        assignments = split_names_for_user(len(rows))
        for row, split in zip(rows, assignments):
            split_rows[split] += 1
            if split != "train":
                continue
            for column in feature_columns:
                add_to_vocab(vocabs[column], row[column], missing_values[column])

    summary = {
        "total_rows": total_rows,
        "user_blocks": user_blocks,
        "split_rows": dict(split_rows),
        "short_user_counts": dict(short_user_counts),
    }
    return vocabs, summary


def write_vocabs(vocabs: dict[str, dict[str, int]], vocab_dir: Path) -> dict[str, str]:
    vocab_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for column, vocab in vocabs.items():
        path = vocab_dir / f"{column}.json"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(vocab, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        paths[column] = str(path)
    return paths


def encode_and_materialize(
    input_path: Path,
    output_dir: Path,
    feature_columns: list[str],
    label_column: str,
    group_column: str,
    vocabs: dict[str, dict[str, int]],
    missing_values: dict[str, set[str]],
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    split_paths = {split: output_dir / f"{split}.csv" for split in SPLITS}
    fieldnames = [label_column] + [f"{column}_idx" for column in feature_columns]
    handles = {
        split: path.open("w", encoding="utf-8", newline="")
        for split, path in split_paths.items()
    }
    writers = {split: csv.DictWriter(handles[split], fieldnames=fieldnames) for split in SPLITS}
    for writer in writers.values():
        writer.writeheader()

    split_rows = Counter()
    label_counts = {split: Counter() for split in SPLITS}
    oov_counts = {split: Counter() for split in SPLITS}
    missing_counts = {split: Counter() for split in SPLITS}
    distinct_groups = {split: set() for split in SPLITS}

    try:
        for _, rows in iter_user_blocks(input_path):
            assignments = split_names_for_user(len(rows))
            for row, split in zip(rows, assignments):
                encoded = {label_column: row[label_column]}
                for column in feature_columns:
                    idx = encode_value(vocabs[column], row[column], missing_values[column])
                    encoded[f"{column}_idx"] = idx
                    if idx == RESERVED_OOV_INDEX:
                        oov_counts[split][column] += 1
                    if idx == RESERVED_MISSING_INDEX:
                        missing_counts[split][column] += 1
                writers[split].writerow(encoded)
                split_rows[split] += 1
                label_counts[split][row[label_column]] += 1
                distinct_groups[split].add(encoded[f"{group_column}_idx"])
    finally:
        for handle in handles.values():
            handle.close()

    user_oov_bad_splits = [
        split for split in ("valid", "test") if oov_counts[split][group_column] != 0
    ]
    if user_oov_bad_splits:
        raise RuntimeError(
            "valid/test user_id OOV should be 0 for user-internal split; "
            f"bad splits: {user_oov_bad_splits}"
        )

    return {
        "split_paths": {split: str(path) for split, path in split_paths.items()},
        "split_rows": dict(split_rows),
        "label_counts": {split: dict(counts) for split, counts in label_counts.items()},
        "oov_counts": {split: dict(counts) for split, counts in oov_counts.items()},
        "missing_counts": {
            split: dict(counts) for split, counts in missing_counts.items()
        },
        "distinct_group_counts": {
            split: len(values) for split, values in distinct_groups.items()
        },
    }


def preprocess_ctr(input_path: Path, output_root: Path, config: dict) -> dict:
    input_path = Path(input_path)
    output_root = Path(output_root)
    feature_columns = list(config["features"]["categorical"])
    label_column = config["label_column"]
    group_column = config["group_column"]
    missing_config = config.get("missing_values", {})
    missing_values = {
        column: normalize_missing_values(missing_config.get(column, list(DEFAULT_MISSING_VALUES)))
        for column in feature_columns
    }
    run_id = make_run_id(input_path, config)
    run_dir = output_root / run_id
    vocab_dir = run_dir / "vocabs"
    materialized_dir = run_dir / "materialized"

    pass1_started_at = time.time()
    vocabs, pass1_summary = build_train_vocabs(
        input_path=input_path,
        feature_columns=feature_columns,
        missing_values=missing_values,
    )
    pass1_summary["elapsed_seconds"] = round(time.time() - pass1_started_at, 3)
    vocab_paths = write_vocabs(vocabs, vocab_dir)
    pass2_started_at = time.time()
    pass2_summary = encode_and_materialize(
        input_path=input_path,
        output_dir=materialized_dir,
        feature_columns=feature_columns,
        label_column=label_column,
        group_column=group_column,
        vocabs=vocabs,
        missing_values=missing_values,
    )
    pass2_summary["elapsed_seconds"] = round(time.time() - pass2_started_at, 3)

    metadata = {
        "run_id": run_id,
        "data_contract_version": DATA_CONTRACT_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "git_commit": git_commit(),
        "input_path": str(input_path),
        "input_name": input_path.name,
        "input_size_bytes": file_size_bytes(input_path),
        "config": config,
        "reserved_indices": {
            "oov": RESERVED_OOV_INDEX,
            "missing": RESERVED_MISSING_INDEX,
            "seen_values_start": 2,
        },
        "split_rule": {
            "description": (
                "Per user block, preserve file order; N<3 -> train only; "
                "N>=3 -> valid=max(1,floor(0.1N)), "
                "test=max(1,floor(0.1N)), train=N-valid-test."
            ),
            "shuffle": False,
            "deduplicate": False,
            "seed_used_by_split": False,
        },
        "feature_columns": feature_columns,
        "label_column": label_column,
        "group_column": group_column,
        "missing_values": {
            column: sorted(values) for column, values in missing_values.items()
        },
        "vocab_sizes": {column: len(vocab) for column, vocab in vocabs.items()},
        "vocab_paths": vocab_paths,
        "pass1": pass1_summary,
        "pass2": pass2_summary,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = run_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return metadata
