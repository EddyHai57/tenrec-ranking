import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch
from torch import nn

from tenrec.models import DeepFM, DcnV2, FieldWiseLogisticRegression, build_model


class TorchModelsTest(unittest.TestCase):
    def test_lr_is_scalar_lookup_sum(self):
        model = FieldWiseLogisticRegression(
            vocab_sizes={"user_id": 5, "item_id": 7},
            feature_columns=["user_id", "item_id"],
        )
        self.assertEqual(model.weights["user_id"].embedding_dim, 1)
        self.assertEqual(model.weights["item_id"].embedding_dim, 1)
        logits = model(
            {
                "user_id": torch.tensor([1, 2, 3], dtype=torch.long),
                "item_id": torch.tensor([2, 3, 4], dtype=torch.long),
            }
        )
        self.assertEqual(tuple(logits.shape), (3,))

    def test_mlp_uses_embedding_dim(self):
        model = build_model(
            {
                "name": "mlp",
                "mlp": {"embedding_dim": 4, "hidden_dims": [8], "dropout": 0.0},
            },
            vocab_sizes={"user_id": 5, "item_id": 7},
            feature_columns=["user_id", "item_id"],
        )
        logits = model(
            {
                "user_id": torch.tensor([1, 2], dtype=torch.long),
                "item_id": torch.tensor([2, 3], dtype=torch.long),
            }
        )
        self.assertEqual(tuple(logits.shape), (2,))

    def test_deepfm_has_fm_terms_and_returns_batch_logits(self):
        model = build_model(
            {
                "name": "deepfm",
                "deepfm": {
                    "embedding_dim": 4,
                    "hidden_dims": [8],
                    "dropout": 0.0,
                },
            },
            vocab_sizes={"user_id": 5, "item_id": 7, "video_category": 3},
            feature_columns=["user_id", "item_id", "video_category"],
        )
        self.assertIsInstance(model, DeepFM)
        self.assertTrue(hasattr(model, "linear_embeddings"))
        self.assertTrue(hasattr(model, "fm_embeddings"))
        self.assertIsInstance(model.deep, nn.Sequential)
        logits = model(
            {
                "user_id": torch.tensor([1, 2], dtype=torch.long),
                "item_id": torch.tensor([2, 3], dtype=torch.long),
                "video_category": torch.tensor([1, 2], dtype=torch.long),
            }
        )
        self.assertEqual(tuple(logits.shape), (2,))

    def test_deepfm_initial_logits_are_not_saturated_by_fm_term(self):
        torch.manual_seed(20260525)
        model = build_model(
            {
                "name": "deepfm",
                "deepfm": {
                    "embedding_dim": 8,
                    "hidden_dims": [16],
                    "dropout": 0.0,
                },
            },
            vocab_sizes={"user_id": 50, "item_id": 70, "video_category": 4},
            feature_columns=["user_id", "item_id", "video_category"],
        )
        logits = model(
            {
                "user_id": torch.randint(0, 50, (128,), dtype=torch.long),
                "item_id": torch.randint(0, 70, (128,), dtype=torch.long),
                "video_category": torch.randint(0, 4, (128,), dtype=torch.long),
            }
        )
        self.assertLess(float(torch.max(torch.abs(logits.detach()))), 1.0)

    def test_dcnv2_has_cross_layers_and_returns_batch_logits(self):
        model = build_model(
            {
                "name": "dcnv2",
                "dcnv2": {
                    "embedding_dim": 4,
                    "cross_layers": 2,
                    "deep_hidden_dims": [8],
                    "dropout": 0.0,
                },
            },
            vocab_sizes={"user_id": 5, "item_id": 7},
            feature_columns=["user_id", "item_id"],
        )
        self.assertIsInstance(model, DcnV2)
        self.assertEqual(len(model.cross_layers), 2)
        self.assertIsInstance(model.deep, nn.Sequential)
        logits = model(
            {
                "user_id": torch.tensor([1, 2, 3], dtype=torch.long),
                "item_id": torch.tensor([2, 3, 4], dtype=torch.long),
            }
        )
        self.assertEqual(tuple(logits.shape), (3,))

    def test_lr_and_dcnv2_accept_numeric_features(self):
        features = {
            "user_id": torch.tensor([1, 2], dtype=torch.long),
            "item_id": torch.tensor([2, 3], dtype=torch.long),
        }
        numeric = torch.tensor([[0.1, -0.2], [1.0, 0.5]], dtype=torch.float32)
        lr = build_model(
            {"name": "lr"},
            vocab_sizes={"user_id": 5, "item_id": 7},
            feature_columns=["user_id", "item_id"],
            numeric_features=["item_hist_ctr", "user_log_impressions"],
        )
        dcnv2 = build_model(
            {
                "name": "dcnv2",
                "dcnv2": {
                    "embedding_dim": 4,
                    "cross_layers": 1,
                    "deep_hidden_dims": [8],
                    "dropout": 0.0,
                },
            },
            vocab_sizes={"user_id": 5, "item_id": 7},
            feature_columns=["user_id", "item_id"],
            numeric_features=["item_hist_ctr", "user_log_impressions"],
        )

        self.assertTrue(lr.uses_numeric_features)
        self.assertTrue(dcnv2.uses_numeric_features)
        self.assertEqual(tuple(lr(features, numeric).shape), (2,))
        self.assertEqual(tuple(dcnv2(features, numeric).shape), (2,))

    def test_dcnv2_uses_small_initialization_and_output_bias(self):
        torch.manual_seed(20260525)
        model = build_model(
            {
                "name": "dcnv2",
                "dcnv2": {
                    "embedding_dim": 8,
                    "cross_layers": 2,
                    "deep_hidden_dims": [16],
                    "dropout": 0.0,
                    "output_bias_init": -1.0,
                },
            },
            vocab_sizes={"user_id": 50, "item_id": 70, "video_category": 4},
            feature_columns=["user_id", "item_id", "video_category"],
        )
        logits = model(
            {
                "user_id": torch.randint(0, 50, (128,), dtype=torch.long),
                "item_id": torch.randint(0, 70, (128,), dtype=torch.long),
                "video_category": torch.randint(0, 4, (128,), dtype=torch.long),
            }
        )
        self.assertAlmostEqual(float(model.output.bias.detach().item()), -1.0, places=6)
        self.assertLess(float(torch.std(logits.detach())), 0.1)
        self.assertAlmostEqual(float(torch.sigmoid(logits.detach()).mean()), 0.2689, delta=0.03)


if __name__ == "__main__":
    unittest.main()
