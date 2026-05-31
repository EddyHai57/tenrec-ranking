import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch

from tenrec.models import Din, build_model


class DinTest(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(20260529)
        self.vocab_sizes = {
            "user_id": 11,
            "item_id": 17,
            "video_category": 4,
            "gender": 5,
            "age": 10,
        }
        self.feature_columns = ["user_id", "item_id", "video_category", "gender", "age"]
        self.model = build_model(
            {
                "name": "din",
                "din": {
                    "embedding_dim": 8,
                    "attention_hidden_dims": [16, 8],
                    "deep_hidden_dims": [32, 16],
                    "dropout": 0.0,
                    "output_bias_init": -1.0,
                    "padding_index": 1,
                },
            },
            vocab_sizes=self.vocab_sizes,
            feature_columns=self.feature_columns,
        )

    def features(self, item_ids=None):
        if item_ids is None:
            item_ids = [2, 3]
        return {
            "user_id": torch.tensor([2, 3], dtype=torch.long),
            "item_id": torch.tensor(item_ids, dtype=torch.long),
            "video_category": torch.tensor([2, 3], dtype=torch.long),
            "gender": torch.tensor([2, 4], dtype=torch.long),
            "age": torch.tensor([2, 5], dtype=torch.long),
        }

    def sequence(self, rows=None):
        if rows is None:
            rows = [
                [0, 1, 2, 3, 1, 4, 5, 6, 7, 8],
                [0, 1, 3, 4, 1, 5, 6, 7, 8, 9],
            ]
        return {"hist_item": torch.tensor(rows, dtype=torch.long)}

    def test_target_and_hist_share_same_embedding_object(self):
        self.assertIsInstance(self.model, Din)
        self.assertIs(self.model.target_embedding, self.model.hist_embedding)
        self.assertEqual(id(self.model.target_embedding), id(self.model.hist_embedding))

    def test_padding_positions_are_masked_but_oov_is_not_masked(self):
        weights = self.model.attention_weights(self.features(), self.sequence())
        padding_mask = self.sequence()["hist_item"].eq(1)
        oov_mask = self.sequence()["hist_item"].eq(0)
        self.assertTrue(torch.all(weights[padding_mask] == 0))
        self.assertTrue(torch.all(weights[oov_mask] != 0))

    def test_attention_depends_on_target_item(self):
        sequence = self.sequence()
        weights_a = self.model.attention_weights(self.features(item_ids=[2, 2]), sequence)
        weights_b = self.model.attention_weights(self.features(item_ids=[4, 4]), sequence)
        self.assertFalse(torch.allclose(weights_a, weights_b))

    def test_all_padding_history_has_zero_user_interest(self):
        features = self.features()
        sequence = self.sequence([[1] * 10, [1] * 10])
        user_interest = self.model.user_interest_vector(features, sequence)
        logits = self.model(features, sequence)
        manual_logits = self.model.logit_from_user_interest(
            features=features,
            user_interest=torch.zeros_like(user_interest),
        )
        self.assertTrue(torch.allclose(user_interest, torch.zeros_like(user_interest)))
        self.assertTrue(torch.allclose(logits, manual_logits))

    def test_no_padding_different_history_values_have_non_identical_attention(self):
        weights = self.model.attention_weights(
            self.features(),
            self.sequence(
                [
                    [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                    [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                ]
            ),
        )
        self.assertFalse(torch.allclose(weights[:, 0], weights[:, 1]))

    def test_forward_returns_batch_logits(self):
        logits = self.model(self.features(), self.sequence())
        self.assertEqual(tuple(logits.shape), (2,))

    def test_forward_with_numeric_features_pipeline(self):
        model = build_model(
            {
                "name": "din",
                "din": {
                    "embedding_dim": 8,
                    "attention_hidden_dims": [16, 8],
                    "deep_hidden_dims": [32, 16],
                    "dropout": 0.0,
                    "output_bias_init": -1.0,
                    "padding_index": 1,
                },
            },
            vocab_sizes=self.vocab_sizes,
            feature_columns=self.feature_columns,
            numeric_features=["f1", "f2", "f3", "f4", "f5", "f6"],
        )
        numeric = torch.zeros([2, 6])
        logits = model(self.features(), self.sequence(), numeric)
        self.assertEqual(tuple(logits.shape), (2,))

    def _build_mode(self, hist_mode, numeric=None):
        return build_model(
            {
                "name": "din",
                "din": {
                    "embedding_dim": 8,
                    "attention_hidden_dims": [16, 8],
                    "deep_hidden_dims": [32, 16],
                    "dropout": 0.0,
                    "output_bias_init": -1.0,
                    "padding_index": 1,
                    "hist_mode": hist_mode,
                },
            },
            vocab_sizes=self.vocab_sizes,
            feature_columns=self.feature_columns,
            numeric_features=numeric,
        )

    def test_hist_mode_meanpool_forward_shape(self):
        model = self._build_mode("meanpool")
        logits = model(self.features(), self.sequence())
        self.assertEqual(tuple(logits.shape), (2,))

    def test_hist_mode_none_forward_shape(self):
        model = self._build_mode("none")
        logits = model(self.features(), self.sequence())
        self.assertEqual(tuple(logits.shape), (2,))

    def test_hist_mode_none_drops_user_interest_dim(self):
        att = self._build_mode("attention")
        non = self._build_mode("none")
        # none 比 attention 的 deep 输入少一个 embedding (user_interest)
        self.assertEqual(att.deep[0].in_features - non.deep[0].in_features, att.embedding_dim)

    def test_meanpool_equals_manual_non_padding_mean(self):
        model = self._build_mode("meanpool")
        features = self.features()
        sequence = self.sequence()
        ui = model.user_interest_vector(features, sequence)
        hist = sequence["hist_item"]
        emb = model.hist_embedding(hist)
        mask = hist.ne(1).to(emb.dtype).unsqueeze(-1)
        manual = (emb * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)
        self.assertTrue(torch.allclose(ui, manual, atol=1e-6))

    def test_invalid_hist_mode_raises(self):
        with self.assertRaises(ValueError):
            self._build_mode("bogus")


if __name__ == "__main__":
    unittest.main()
