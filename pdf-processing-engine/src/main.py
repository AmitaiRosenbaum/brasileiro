
import os
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine


SCRIPT_DIR = Path(__file__).parent


def main():
    book_name = 'SongBook_BossaNova_1'
    file_name = book_name + '.pdf'
    engine = ClassificationEngine(book_name)
    original_file_path = str(SCRIPT_DIR / "music" / file_name)
    ocr_file_path = SCRIPT_DIR / 'music' / f'ocr_{file_name}'

    # Add OCR layer if it does not exist
    if not os.path.exists(ocr_file_path):
        engine.ocr(original_file_path, str(ocr_file_path))

    # Set engine's pages
    engine.set_pages_from_file(
        str(ocr_file_path), preamble=30, max_pages=137, redo=True)

    # Train lda
    engine.lda.train()

    engine.classify_pages()

    for page in engine.pages:
        if not page.type and not page.potential_titles:
            print(page.index, page.artist)

    print('hey')
    # Artist extraction
    # count = 0
    # labels = engine.lda.label_pages()
    # for i, label in enumerate(labels):
    #     if not label:
    #         print(count, engine.pages[i].words[0])

    engine.transformer.split(
        ocr_file_path, SCRIPT_DIR / 'music' / 'split', skip=30)


if __name__ == '__main__':
    main()
