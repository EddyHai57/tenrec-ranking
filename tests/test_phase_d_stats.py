import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.preprocess_ctr_stats import (
    build_count_table,
    smoothed_ctr,
    preprocess_stats_features,
)


class PhaseDStatsTest(unittest.TestCase):
    def test_smoothed_ctr_falls_back_to_global_prior_for_oov(self):
        self.assertAlmostEqual(
            smoothed_ctr(clicks=0, impressions=0, global_ctr=0.25, alpha=20.0),
            0.25,
        )
        self.assertAlmostEqual(
            smoothed_ctr(clicks=2, impressions=4, global_ctr=0.25, alpha=20.0),
            (2 + 20 * 0.25) / (4 + 20),
        )

    def test_oof_excludes_current_fold_from_train_encoding(self):
        rows = [
            {"click": "1", "item_id_idx": "10"},
            {"click": "0", "item_id_idx": "10"},
            {"click": "0", "item_id_idx": "10"},
            {"click": "0", "item_id_idx": "20"},
        ]
        full = build_count_table(rows, lambda row: row["item_id_idx"])
        fold0 = build_count_table(rows[:1], lambda row: row["item_id_idx"])
        other_folds = full.subtract(fold0)
        self.assertEqual(full.counts["10"].clicks, 1.0)
        self.assertEqual(full.counts["10"].impressions, 3.0)
        self.assertEqual(other_folds.counts["10"].clicks, 0.0)
        self.assertEqual(other_folds.counts["10"].impressions, 2.0)

    def test_preprocess_stats_uses_train_only_for_valid_and_test(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source"
            materialized = source / "materialized"
            materialized.mkdir(parents=True)
            header = ["click", "user_id_idx", "item_id_idx", "video_category_idx", "gender_idx", "age_idx"]
            split_rows = {
                "train": [
                    ["1", "2", "10", "3", "1", "1"],
                    ["0", "2", "10", "3", "1", "1"],
                    ["0", "4", "20", "5", "1", "1"],
                    ["1", "4", "20", "5", "1", "1"],
                ],
                "valid": [
                    ["1", "9", "99", "8", "1", "1"],
                ],
                "test": [
                    ["0", "2", "10", "3", "1", "1"],
                ],
            }
            for split, rows in split_rows.items():
                with (materialized / f"{split}.csv").open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(header)
                    writer.writerows(rows)
            metadata = {
                "run_id": "fixture",
                "feature_columns": ["user_id", "item_id", "video_category", "gender", "age"],
                "sequence_features": {},
                "vocab_sizes": {
                    "user_id": 10,
                    "item_id": 100,
                    "video_category": 10,
                    "gender": 3,
                    "age": 3,
                },
                "pass2": {
                    "split_paths": {
                        split: str(materialized / f"{split}.csv")
                        for split in ("train", "valid", "test")
                    },
                    "label_counts": {
                        "train": {"0": 2, "1": 2},
                        "valid": {"1": 1},
                        "test": {"0": 1},
                    },
                },
            }
            metadata_path = source / "metadata.json"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            result = preprocess_stats_features(
                source_metadata_path=metadata_path,
                output_root=tmp / "out",
                alpha=20.0,
                folds=2,
                seed=20260525,
                mode="oof",
                overwrite=True,
            )

            self.assertEqual(result["source_run_id"], "fixture")
            self.assertIn("numeric_features", result)
            self.assertEqual(
                result["numeric_features"]["implementation"],
                "streaming_fold_out",
            )
            valid_path = Path(result["pass2"]["split_paths"]["valid"])
            with valid_path.open("r", encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(float(row["item_log_impressions"]), 0.0)
            self.assertEqual(result["numeric_features"]["lookup_scope"]["valid"], "train_only")
            self.assertEqual(result["numeric_features"]["lookup_scope"]["test"], "train_only")


if __name__ == "__main__":
    unittest.main()
