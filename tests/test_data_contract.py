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


if __name__ == "__main__":
    unittest.main()
