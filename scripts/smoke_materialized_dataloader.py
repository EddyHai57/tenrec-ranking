import argparse
import csv
import json
from itertools import islice
from pathlib import Path


def read_batch(path: Path, batch_size: int):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(islice(reader, batch_size))
    if not rows:
        raise ValueError(f"No rows read from {path}")
    return rows


def summarize_batch(rows):
    columns = list(rows[0].keys())
    labels = [int(row["click"]) for row in rows]
    features = [column for column in columns if column != "click"]
    return {
        "batch_rows": len(rows),
        "columns": columns,
        "feature_columns": features,
        "click_positive_count": sum(labels),
        "click_negative_count": len(labels) - sum(labels),
        "feature_min_max": {
            column: {
                "min": min(int(row[column]) for row in rows),
                "max": max(int(row[column]) for row in rows),
            }
            for column in features
        },
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test materialized CTR split files.")
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def main():
    args = parse_args()
    metadata_path = Path(args.metadata)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    result = {}
    for split, split_path in metadata["pass2"]["split_paths"].items():
        rows = read_batch(Path(split_path), args.batch_size)
        result[split] = summarize_batch(rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
