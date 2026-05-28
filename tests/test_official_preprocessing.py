import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scripts.preprocess_ctr_data_official import preprocess_official_compatible


class OfficialPreprocessingTest(unittest.TestCase):
    def test_sampling_split_and_vocab_reuse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source_run = tmp / "source"
            materialized = source_run / "materialized"
            vocabs = source_run / "vocabs"
            materialized.mkdir(parents=True)
            vocabs.mkdir()
            for name, vocab in {
                "user_id": {"__OOV__": 0, "__MISSING__": 1, "u1": 2, "u2": 3},
                "item_id": {"__OOV__": 0, "__MISSING__": 1, "i1": 2, "i2": 3},
                "video_category": {"__OOV__": 0, "__MISSING__": 1, "c1": 2},
                "gender": {"__OOV__": 0, "__MISSING__": 1, "g1": 2},
                "age": {"__OOV__": 0, "__MISSING__": 1, "a1": 2},
            }.items():
                (vocabs / f"{name}.json").write_text(
                    json.dumps(vocab, ensure_ascii=False), encoding="utf-8"
                )

            header = ["click", "user_id_idx", "item_id_idx", "video_category_idx", "gender_idx", "age_idx"]
            rows = []
            rows.extend([["1", "2", "2", "2", "2", "2"] for _ in range(20)])
            rows.extend([["0", "3", "3", "2", "2", "2"] for _ in range(40)])
            for split in ("train", "valid", "test"):
                with (materialized / f"{split}.csv").open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(header)
                    if split == "train":
                        writer.writerows(rows)

            source_metadata = {
                "run_id": "ctr-972e0dcb2b8d",
                "data_contract_version": "ctr_mvp_v0.1",
                "feature_columns": ["user_id", "item_id", "video_category", "gender", "age"],
                "label_column": "click",
                "group_column": "user_id",
                "reserved_indices": {"oov": 0, "missing": 1, "seen_values_start": 2},
                "vocab_sizes": {
                    "user_id": 4,
                    "item_id": 4,
                    "video_category": 3,
                    "gender": 3,
                    "age": 3,
                },
                "vocab_paths": {
                    name: str(vocabs / f"{name}.json")
                    for name in ["user_id", "item_id", "video_category", "gender", "age"]
                },
                "pass2": {
                    "split_paths": {
                        split: str(materialized / f"{split}.csv")
                        for split in ("train", "valid", "test")
                    }
                },
            }
            source_metadata_path = source_run / "metadata.json"
            source_metadata_path.write_text(
                json.dumps(source_metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            metadata = preprocess_official_compatible(
                source_metadata_path=source_metadata_path,
                output_root=tmp / "out",
                seed=20260525,
                neg_sampling_ratio=2,
                train_ratio=0.8,
                valid_ratio=0.1,
                test_ratio=0.1,
                shuffle_bucket_count=4,
            )

            label_counts = metadata["official"]["sample_label_counts"]
            self.assertEqual(label_counts["1"], 20)
            self.assertAlmostEqual(label_counts["0"] / label_counts["1"], 2.0, delta=0.04)

            split_rows = metadata["pass2"]["split_rows"]
            total = sum(split_rows.values())
            self.assertAlmostEqual(split_rows["train"] / total, 0.8, delta=0.05)
            self.assertAlmostEqual(split_rows["valid"] / total, 0.1, delta=0.05)
            self.assertAlmostEqual(split_rows["test"] / total, 0.1, delta=0.05)

            self.assertEqual(metadata["protocol"], "official-compatible")
            self.assertEqual(metadata["official"]["vocab_source"], "ctr-972e0dcb2b8d (reuse)")
            self.assertEqual(metadata["vocab_sizes"], source_metadata["vocab_sizes"])
            for name, path in metadata["vocab_paths"].items():
                self.assertEqual(
                    json.loads(Path(path).read_text(encoding="utf-8")),
                    json.loads(Path(source_metadata["vocab_paths"][name]).read_text(encoding="utf-8")),
                )


if __name__ == "__main__":
    unittest.main()
