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


if __name__ == "__main__":
    unittest.main()
