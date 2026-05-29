import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch

from tenrec.torch_data import (
    iter_materialized_batches,
    iter_tensor_batches,
    load_materialized_tensor_table,
)


class TorchDataTest(unittest.TestCase):
    def write_materialized(self, path: Path) -> None:
        rows = [
            ["click", "user_id_idx", "item_id_idx", "video_category_idx", "gender_idx", "age_idx"],
            [0, 10, 100, 1, 2, 3],
            [1, 11, 101, 1, 2, 4],
            [0, 12, 102, 2, 3, 5],
            [1, 13, 103, 2, 3, 6],
            [0, 14, 104, 3, 4, 7],
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)

    def write_materialized_with_hist(self, path: Path) -> None:
        rows = [
            [
                "click",
                "user_id_idx",
                "item_id_idx",
                "video_category_idx",
                "gender_idx",
                "age_idx",
                "hist_1_idx",
                "hist_2_idx",
                "hist_3_idx",
            ],
            [0, 10, 100, 1, 2, 3, 100, 1, 0],
            [1, 11, 101, 1, 2, 4, 0, 1, 101],
            [0, 12, 102, 2, 3, 5, 102, 103, 1],
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)

    def write_materialized_with_numeric(self, path: Path) -> None:
        rows = [
            [
                "click",
                "user_id_idx",
                "item_id_idx",
                "video_category_idx",
                "gender_idx",
                "age_idx",
                "item_hist_ctr",
                "user_log_impressions",
            ],
            [0, 10, 100, 1, 2, 3, -0.5, 1.25],
            [1, 11, 101, 1, 2, 4, 0.75, -0.25],
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)

    def test_tensor_batches_match_csv_batches_without_shuffle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "train.csv"
            self.write_materialized(path)
            feature_columns = ["user_id", "item_id", "video_category", "gender", "age"]
            device = torch.device("cpu")

            csv_batches = list(
                iter_materialized_batches(
                    path=path,
                    feature_columns=feature_columns,
                    batch_size=2,
                    device=device,
                )
            )
            table = load_materialized_tensor_table(
                path=path,
                feature_columns=feature_columns,
                device=device,
            )
            tensor_batches = list(
                iter_tensor_batches(
                    table=table,
                    batch_size=2,
                    shuffle=False,
                )
            )

            self.assertEqual(len(tensor_batches), len(csv_batches))
            for csv_batch, tensor_batch in zip(csv_batches, tensor_batches):
                self.assertTrue(torch.equal(tensor_batch["labels"], csv_batch["labels"]))
                for column in feature_columns:
                    self.assertTrue(
                        torch.equal(tensor_batch["features"][column], csv_batch["features"][column])
                    )

    def test_tensor_batches_use_deterministic_generator_shuffle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "train.csv"
            self.write_materialized(path)
            feature_columns = ["user_id", "item_id", "video_category", "gender", "age"]
            device = torch.device("cpu")
            table = load_materialized_tensor_table(
                path=path,
                feature_columns=feature_columns,
                device=device,
            )

            generator_a = torch.Generator(device=device).manual_seed(20260525)
            generator_b = torch.Generator(device=device).manual_seed(20260525)
            first = list(iter_tensor_batches(table, batch_size=3, shuffle=True, generator=generator_a))
            second = list(iter_tensor_batches(table, batch_size=3, shuffle=True, generator=generator_b))

            self.assertTrue(torch.equal(first[0]["labels"], second[0]["labels"]))
            self.assertFalse(torch.equal(first[0]["labels"], table.labels[:3]))

    def test_csv_and_tensor_batches_include_hist_sequence_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "train.csv"
            self.write_materialized_with_hist(path)
            feature_columns = ["user_id", "item_id", "video_category", "gender", "age"]
            sequence_features = {
                "hist_item": {
                    "encoded_columns": ["hist_1_idx", "hist_2_idx", "hist_3_idx"],
                }
            }
            device = torch.device("cpu")

            csv_batch = next(
                iter_materialized_batches(
                    path=path,
                    feature_columns=feature_columns,
                    batch_size=2,
                    device=device,
                    sequence_features=sequence_features,
                )
            )
            table = load_materialized_tensor_table(
                path=path,
                feature_columns=feature_columns,
                device=device,
                sequence_features=sequence_features,
            )
            tensor_batch = next(iter_tensor_batches(table=table, batch_size=2, shuffle=False))

            self.assertEqual(tuple(csv_batch["sequence_features"]["hist_item"].shape), (2, 3))
            self.assertTrue(
                torch.equal(
                    csv_batch["sequence_features"]["hist_item"],
                    torch.tensor([[100, 1, 0], [0, 1, 101]], dtype=torch.long),
                )
            )
            self.assertTrue(
                torch.equal(
                    tensor_batch["sequence_features"]["hist_item"],
                    csv_batch["sequence_features"]["hist_item"],
                )
            )

    def test_csv_and_tensor_batches_include_numeric_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "train.csv"
            self.write_materialized_with_numeric(path)
            feature_columns = ["user_id", "item_id", "video_category", "gender", "age"]
            numeric_features = ["item_hist_ctr", "user_log_impressions"]
            device = torch.device("cpu")

            csv_batch = next(
                iter_materialized_batches(
                    path=path,
                    feature_columns=feature_columns,
                    batch_size=2,
                    device=device,
                    numeric_features=numeric_features,
                )
            )
            table = load_materialized_tensor_table(
                path=path,
                feature_columns=feature_columns,
                device=device,
                numeric_features=numeric_features,
            )
            tensor_batch = next(iter_tensor_batches(table=table, batch_size=2, shuffle=False))

            expected = torch.tensor([[-0.5, 1.25], [0.75, -0.25]], dtype=torch.float32)
            self.assertTrue(torch.allclose(csv_batch["numeric_features"], expected))
            self.assertTrue(torch.allclose(tensor_batch["numeric_features"], expected))


if __name__ == "__main__":
    unittest.main()
