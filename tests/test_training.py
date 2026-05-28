import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.training import data_loader_name, resolve_model_config, train_base_logit


class TrainingConfigTest(unittest.TestCase):
    def test_data_loader_defaults_to_csv(self):
        self.assertEqual(data_loader_name({"data": {}}), "csv")

    def test_data_loader_accepts_tensor(self):
        self.assertEqual(data_loader_name({"data": {"loader": "tensor"}}), "tensor")

    def test_data_loader_rejects_unknown_loader(self):
        with self.assertRaises(ValueError):
            data_loader_name({"data": {"loader": "parquet"}})

    def test_train_base_logit_uses_train_label_counts(self):
        metadata = {
            "pass2": {
                "label_counts": {
                    "train": {
                        "0": 80,
                        "1": 20,
                    }
                }
            }
        }
        self.assertAlmostEqual(train_base_logit(metadata), math.log(20 / 80))

    def test_resolve_model_config_replaces_dcnv2_train_base_rate_bias(self):
        config = {
            "model": {
                "name": "dcnv2",
                "dcnv2": {
                    "embedding_dim": 8,
                    "cross_layers": 2,
                    "deep_hidden_dims": [16],
                    "output_bias_init": "train_base_rate",
                },
            }
        }
        metadata = {
            "pass2": {
                "label_counts": {
                    "train": {
                        "0": 80,
                        "1": 20,
                    }
                }
            }
        }
        model_config = resolve_model_config(config, metadata)
        self.assertAlmostEqual(model_config["dcnv2"]["output_bias_init"], math.log(20 / 80))
        self.assertEqual(config["model"]["dcnv2"]["output_bias_init"], "train_base_rate")


if __name__ == "__main__":
    unittest.main()
