
import os
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine


SCRIPT_DIR = Path(__file__).parent


def main():
    book_name = 'SongBook_BossaNova_1'
    file_name = book_name + '.pdf'
    engine = ClassificationEngine(book_name)
    original_file_path = str(SCRIPT_DIR / "music" / file_name)
    ocr_file_path = str(SCRIPT_DIR / 'music' / f'ocr_{file_name}')

    # Add OCR layer if it does not exist
    if not os.path.exists(ocr_file_path):
        engine.ocr(original_file_path, ocr_file_path)

    # Set engine's pages
    engine.set_pages_from_file(ocr_file_path, preamble=30)

    # Train lda
    engine.lda.train()


if __name__ == '__main__':
    main()
