import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.metrics import binary_auc, impression_weighted_gauc


FEATURE_COLUMNS = [
    "user_id_idx",
    "item_id_idx",
    "video_category_idx",
    "gender_idx",
    "age_idx",
]


def load_materialized(path: Path, max_rows: int | None = None):
    x_rows = []
    y = []
    groups = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            if max_rows is not None and idx >= max_rows:
                break
            x_rows.append([int(row[column]) for column in FEATURE_COLUMNS])
            y.append(int(row["click"]))
            groups.append(int(row["user_id_idx"]))
    if not x_rows:
        raise ValueError(f"No rows loaded from {path}")
    return np.asarray(x_rows, dtype=np.int64), np.asarray(y, dtype=np.int64), np.asarray(groups)


def evaluate(name: str, model, x, y, groups):
    probabilities = model.predict_proba(x)[:, 1]
    gauc = impression_weighted_gauc(y, probabilities, groups)
    return {
        "split": name,
        "rows": int(len(y)),
        "positive_rate": float(y.mean()),
        "auc": float(binary_auc(y, probabilities)),
        "logloss": float(log_loss(y, probabilities, labels=[0, 1])),
        "gauc": gauc.gauc,
        "gauc_valid_user_count": gauc.valid_user_count,
        "gauc_total_user_count": gauc.total_user_count,
        "gauc_valid_row_count": gauc.valid_row_count,
        "gauc_total_row_count": gauc.total_row_count,
        "gauc_row_coverage_rate": gauc.row_coverage_rate,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run sklearn LR learnability smoke on materialized CTR data.")
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--max-train-rows", type=int, default=100000)
    parser.add_argument("--max-valid-rows", type=int, default=50000)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    train_path = Path(metadata["pass2"]["split_paths"]["train"])
    valid_path = Path(metadata["pass2"]["split_paths"]["valid"])

    x_train, y_train, train_groups = load_materialized(train_path, args.max_train_rows)
    x_valid, y_valid, valid_groups = load_materialized(valid_path, args.max_valid_rows)

    model = Pipeline(
        steps=[
            (
                "onehot",
                ColumnTransformer(
                    transformers=[
                        (
                            "categorical",
                            OneHotEncoder(handle_unknown="ignore"),
                            list(range(len(FEATURE_COLUMNS))),
                        )
                    ]
                ),
            ),
            (
                "lr",
                LogisticRegression(
                    max_iter=200,
                    solver="liblinear",
                    random_state=20260525,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)

    result = {
        "metadata": str(Path(args.metadata)),
        "feature_columns": FEATURE_COLUMNS,
        "model": "sklearn LogisticRegression one-hot categorical smoke",
        "max_train_rows": args.max_train_rows,
        "max_valid_rows": args.max_valid_rows,
        "train": evaluate("train", model, x_train, y_train, train_groups),
        "valid": evaluate("valid", model, x_valid, y_valid, valid_groups),
        "known_limitations": [
            "smoke sample only; not a formal model result",
            "uses materialized encoded data to test preprocessing pipeline",
        ],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
