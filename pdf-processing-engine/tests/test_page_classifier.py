import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from engine.PageClassifier import PageClassifier  # noqa: E402


class PageClassifierTests(unittest.TestCase):
    def test_supervised_predictions_are_sequence_refined(self):
        pages = [Mock(), Mock()]
        classifier = PageClassifier(pages, labels=[0, 1])
        classifier._supervised_model = Mock()
        classifier._supervised_model.predict.return_value = [1, 0]
        classifier._supervised_vector = Mock(return_value=(0.0,))
        classifier._sequence_refiner = Mock()
        classifier._sequence_refiner.refine.return_value = [0, 1]

        self.assertEqual(classifier.label_pages(), [0, 1])
        classifier._sequence_refiner.refine.assert_called_once_with(pages, [1, 0])


if __name__ == "__main__":
    unittest.main()
