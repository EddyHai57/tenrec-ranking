import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch

from tenrec.models import FieldWiseLogisticRegression, build_model


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


if __name__ == "__main__":
    unittest.main()
