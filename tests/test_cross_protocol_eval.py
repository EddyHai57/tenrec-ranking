import csv
import math
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scripts.cross_protocol_eval import evaluate_checkpoint
from tenrec.models import build_model


class CrossProtocolEvalTest(unittest.TestCase):
    def test_loads_checkpoint_and_evaluates_metadata_test_split(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            materialized = tmp / "materialized"
            materialized.mkdir()
            test_path = materialized / "test.csv"
            with test_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["click", "user_id_idx", "item_id_idx"])
                writer.writerows(
                    [
                        [1, 2, 2],
                        [0, 2, 3],
                        [0, 3, 2],
                        [0, 3, 3],
                    ]
                )

            metadata = {
                "run_id": "fixture-eval",
                "feature_columns": ["user_id", "item_id"],
                "sequence_features": {},
                "vocab_sizes": {"user_id": 4, "item_id": 4},
                "pass2": {
                    "split_paths": {"test": str(test_path)},
                    "label_counts": {
                        "train": {"0": 3, "1": 1},
                        "test": {"0": 3, "1": 1},
                    },
                },
            }
            metadata_path = tmp / "metadata.json"
            metadata_path.write_text(
                __import__("json").dumps(metadata, ensure_ascii=False),
                encoding="utf-8",
            )

            model_config = {"name": "lr", "lr": {"parameterization": "scalar_lookup_sum"}}
            model = build_model(
                model_config=model_config,
                vocab_sizes=metadata["vocab_sizes"],
                feature_columns=metadata["feature_columns"],
            )
            checkpoint_path = tmp / "best.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "config": {"model": model_config},
                    "vocab_sizes": metadata["vocab_sizes"],
                },
                checkpoint_path,
            )

            result = evaluate_checkpoint(
                checkpoint_path=checkpoint_path,
                metadata_path=metadata_path,
                device_name="cpu",
                batch_size=2,
            )

            self.assertEqual(result["test_run_id"], "fixture-eval")
            self.assertEqual(result["test_rows"], 4)
            self.assertAlmostEqual(result["mean_pred"], 0.5)
            self.assertAlmostEqual(result["mean_label"], 0.25)
            self.assertAlmostEqual(result["pcoc"], 2.0)
            self.assertAlmostEqual(result["auc"], 0.5)
            self.assertAlmostEqual(result["gauc"], 0.5)
            self.assertAlmostEqual(result["gauc_row_coverage_rate"], 0.5)
            self.assertAlmostEqual(result["logloss"], math.log(2.0))


if __name__ == "__main__":
    unittest.main()
