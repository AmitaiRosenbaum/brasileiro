
import os
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine


SCRIPT_DIR = Path(__file__).parent


def process_book(book_name: str, preamble: int, max_pages: int = 2**1000):
    print(f'Starting {book_name}')
    file_name = book_name + '.pdf'
    engine = ClassificationEngine(book_name)
    original_file_path = str(SCRIPT_DIR / "music" / file_name)
    ocr_file_path = SCRIPT_DIR / 'music' / f'ocr_{file_name}'

    # Add OCR layer if it does not exist
    if not os.path.exists(ocr_file_path):
        print(f'Adding OCR Layer')
        engine.ocr(original_file_path, str(ocr_file_path))

    # Set engine's pages
    engine.set_pages_from_file(
        str(ocr_file_path), preamble=preamble, max_pages=max_pages)

    # Train lda
    engine.lda.train()

    engine.classify_pages()

    for page in engine.pages:
        if not page.type:
            print(page.index, page.title, page.artist)

    engine.transformer.split(
        ocr_file_path, SCRIPT_DIR / 'music' / 'split', skip=preamble)


def main():
    # process_book('SongBook_BossaNova_1', 30, 137)
    # process_book('SongBook_BossaNova_2', 1)
    # process_book('SongBook_BossaNova_3', 6)
    # process_book('SongBook_BossaNova_4', 5)
    process_book('SongBook_BossaNova_5', 5, 136)


if __name__ == '__main__':
    main()
