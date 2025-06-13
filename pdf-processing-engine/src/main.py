
import os
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine


SCRIPT_DIR = Path(__file__).parent


def main():
    engine = ClassificationEngine()
    original_file_path = str(SCRIPT_DIR / "music/SongBook_BossaNova_1.pdf")
    ocr_file_path = str(SCRIPT_DIR / 'music/ocr_SongBook_BossaNova_1.pdf')
    if not os.path.exists(ocr_file_path):
        engine.ocr(original_file_path, ocr_file_path)
    engine.set_pages_from_file(ocr_file_path)


if __name__ == '__main__':
    main()
