import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tenrec.metrics import binary_auc, binary_log_loss, impression_weighted_gauc


class MetricsTest(unittest.TestCase):
    def test_auc_known_answers(self):
        y_true = [0, 0, 1, 1]
        self.assertEqual(binary_auc(y_true, [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertEqual(binary_auc(y_true, [0.9, 0.8, 0.2, 0.1]), 0.0)
        self.assertEqual(binary_auc(y_true, [0.5, 0.5, 0.5, 0.5]), 0.5)

    def test_auc_single_class_raises(self):
        with self.assertRaises(ValueError):
            binary_auc([1, 1], [0.8, 0.9])
        with self.assertRaises(ValueError):
            binary_auc([0, 0], [0.1, 0.2])

    def test_log_loss_known_answer(self):
        result = binary_log_loss([1, 0], [0.9, 0.2])
        self.assertAlmostEqual(result, 0.164252033486018, places=12)

    def test_gauc_skips_single_class_users_and_reports_coverage(self):
        y_true = [0, 1, 0, 1, 1, 0, 0]
        y_score = [0.1, 0.9, 0.8, 0.7, 0.6, 0.2, 0.3]
        groups = ["u1", "u1", "u2", "u2", "u3", "u4", "u4"]
        result = impression_weighted_gauc(y_true, y_score, groups)
        self.assertEqual(result.valid_user_count, 2)
        self.assertEqual(result.only_positive_user_count, 1)
        self.assertEqual(result.only_negative_user_count, 1)
        self.assertEqual(result.valid_row_count, 4)
        self.assertEqual(result.total_row_count, 7)
        self.assertAlmostEqual(result.row_coverage_rate, 4 / 7)
        self.assertAlmostEqual(result.gauc, 0.5)


if __name__ == "__main__":
    unittest.main()
