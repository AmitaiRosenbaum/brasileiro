import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from engine.ClassificationEngine import ClassificationEngine  # noqa: E402


class ClassificationEngineTests(unittest.TestCase):
    @patch("engine.ClassificationEngine.ocrmypdf.ocr")
    def test_normal_ocr_preserves_existing_text(self, ocr):
        ClassificationEngine("book").ocr("in.pdf", "out.pdf", ["por", "eng"])

        ocr.assert_called_once_with(
            "in.pdf",
            "out.pdf",
            language=["por", "eng"],
            force_ocr=False,
            skip_text=True,
        )

    @patch("engine.ClassificationEngine.ocrmypdf.ocr")
    def test_forced_ocr_replaces_bogus_existing_text(self, ocr):
        ClassificationEngine("book").ocr(
            "in.pdf", "out.pdf", ["por", "eng"], force_ocr=True
        )

        ocr.assert_called_once_with(
            "in.pdf",
            "out.pdf",
            language=["por", "eng"],
            force_ocr=True,
        )


if __name__ == "__main__":
    unittest.main()
