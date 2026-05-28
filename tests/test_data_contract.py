import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.data import (
    RESERVED_MISSING_INDEX,
    RESERVED_OOV_INDEX,
    encode_value,
    empty_vocab,
    preprocess_ctr,
    split_counts_for_user,
)


class DataContractTest(unittest.TestCase):
    def test_split_integer_formula(self):
        expected = {
            0: (0, 0, 0),
            1: (1, 0, 0),
            2: (2, 0, 0),
            3: (1, 1, 1),
            7: (5, 1, 1),
            10: (8, 1, 1),
            99: (81, 9, 9),
            100: (80, 10, 10),
        }
        for row_count, counts in expected.items():
            result = split_counts_for_user(row_count)
            self.assertEqual((result.train, result.valid, result.test), counts)

    def test_missing_precedes_oov(self):
        vocab = empty_vocab()
        self.assertEqual(encode_value(vocab, "\\N", {"\\N"}), RESERVED_MISSING_INDEX)
        self.assertEqual(encode_value(vocab, "new_value", {"\\N"}), RESERVED_OOV_INDEX)

    def test_preprocess_train_only_vocab_and_user_oov(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "fixture.csv"
            rows = [
                ["user_id", "item_id", "click", "video_category", "gender", "age"],
                ["u1", "i_train", "0", "0", "1", "2"],
                ["u1", "i_valid", "1", "\\N", "1", "2"],
                ["u1", "i_test", "0", "9", "1", "2"],
                ["u2", "i2", "1", "1", "0", "3"],
                ["u2", "i3", "0", "1", "0", "3"],
            ]
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            config = {
                "input_path": str(input_path),
                "output_root": str(tmp / "out"),
                "label_column": "click",
                "group_column": "user_id",
                "features": {
                    "categorical": ["user_id", "item_id", "video_category", "gender", "age"]
                },
                "missing_values": {
                    "user_id": ["", "\\N"],
                    "item_id": ["", "\\N"],
                    "video_category": ["", "\\N"],
                    "gender": ["", "\\N"],
                    "age": ["", "\\N"],
                },
            }
            metadata = preprocess_ctr(input_path, tmp / "out", config)
            self.assertEqual(metadata["pass2"]["split_rows"], {"train": 3, "valid": 1, "test": 1})
            self.assertEqual(metadata["pass2"]["oov_counts"]["valid"]["item_id"], 1)
            self.assertEqual(metadata["pass2"]["oov_counts"]["test"]["item_id"], 1)
            self.assertNotIn("user_id", metadata["pass2"]["oov_counts"]["valid"])
            self.assertNotIn("user_id", metadata["pass2"]["oov_counts"]["test"])
            self.assertEqual(metadata["pass2"]["missing_counts"]["valid"]["video_category"], 1)

    def test_preprocess_hist_uses_item_vocab_without_extending_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "fixture_hist.csv"
            rows = [
                [
                    "user_id",
                    "item_id",
                    "click",
                    "video_category",
                    "gender",
                    "age",
                    "hist_1",
                    "hist_2",
                    "hist_3",
                ],
                ["u1", "i_train_u1", "0", "0", "1", "2", "i_train_u1", "0", "i_future"],
                ["u1", "i_valid_u1", "1", "0", "1", "2", "i_train_u2", "", "i_valid_u1"],
                ["u1", "i_test_u1", "0", "0", "1", "2", "\\N", "i_train_u1", "outside"],
                ["u2", "i_train_u2", "1", "1", "0", "3", "i_train_u2", "0", "i_valid_u1"],
                ["u2", "i_valid_u2", "0", "1", "0", "3", "i_train_u1", "", "i_valid_u2"],
                ["u2", "i_test_u2", "1", "1", "0", "3", "\\N", "i_train_u2", "outside"],
            ]
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            config = {
                "input_path": str(input_path),
                "output_root": str(tmp / "out"),
                "label_column": "click",
                "group_column": "user_id",
                "features": {
                    "categorical": ["user_id", "item_id", "video_category", "gender", "age"]
                },
                "sequence_features": {
                    "hist_item": {
                        "columns": ["hist_1", "hist_2", "hist_3"],
                        "vocab_source": "item_id",
                        "padding_index": RESERVED_MISSING_INDEX,
                        "oov_index": RESERVED_OOV_INDEX,
                    }
                },
                "missing_values": {
                    "user_id": ["", "\\N"],
                    "item_id": ["", "\\N"],
                    "video_category": ["", "\\N"],
                    "gender": ["", "\\N"],
                    "age": ["", "\\N"],
                    "hist_item": ["", "0", "\\N"],
                },
            }

            metadata = preprocess_ctr(input_path, tmp / "out", config)

            self.assertEqual(metadata["vocab_sizes"]["item_id"], 4)
            self.assertEqual(
                metadata["sequence_features"]["hist_item"]["vocab_size"],
                metadata["vocab_sizes"]["item_id"],
            )
            self.assertEqual(
                metadata["sequence_features"]["hist_item"]["encoded_columns"],
                ["hist_1_idx", "hist_2_idx", "hist_3_idx"],
            )
            self.assertNotIn("hist_item", metadata["vocab_sizes"])
            self.assertEqual(
                metadata["pass2"]["sequence_padding_counts"]["train"]["hist_item"]["hist_2"],
                2,
            )
            self.assertEqual(
                metadata["pass2"]["sequence_padding_counts"]["test"]["hist_item"]["hist_1"],
                2,
            )
            self.assertEqual(
                metadata["pass2"]["sequence_oov_counts"]["train"]["hist_item"]["hist_3"],
                2,
            )
            self.assertEqual(
                metadata["pass2"]["sequence_oov_counts"]["valid"]["hist_item"]["hist_3"],
                2,
            )

            train_path = Path(metadata["pass2"]["split_paths"]["train"])
            with train_path.open("r", encoding="utf-8", newline="") as handle:
                first_train = next(csv.DictReader(handle))
            self.assertEqual(int(first_train["hist_1_idx"]), 2)
            self.assertEqual(int(first_train["hist_2_idx"]), RESERVED_MISSING_INDEX)
            self.assertEqual(int(first_train["hist_3_idx"]), RESERVED_OOV_INDEX)


if __name__ == "__main__":
    unittest.main()
