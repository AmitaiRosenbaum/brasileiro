
import os
import argparse
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine
from correct_songs_with_llm import correct_songs


SCRIPT_DIR = Path(__file__).parent


def get_default_training_pages():
    engine = ClassificationEngine('SongBook_BossaNova_1')
    ocr_file_path = SCRIPT_DIR / 'music' / 'ocr_SongBook_BossaNova_1.pdf'
    engine.set_pages_from_file(str(ocr_file_path), preamble=30, max_pages=70)
    return engine.pages


def process_book(
    book_name: str,
    preamble: int,
    max_pages: int = 2**1000,
    training_pages=None,
):
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
        str(ocr_file_path),
        preamble=preamble,
        max_pages=max_pages,
        training_pages=training_pages,
    )

    engine.classifier.train()

    engine.classify_pages()

    for page in engine.pages:
        if not page.type:
            print(page.index, page.title, page.artist)

    engine.transformer.split(
        ocr_file_path, SCRIPT_DIR / 'music' / 'split', skip=preamble)


def main(correct_songs_with_llm: bool = False):
    training_pages = get_default_training_pages()
    process_book('SongBook_BossaNova_1', 30, 137, training_pages=training_pages)
    process_book('SongBook_BossaNova_2', 1, training_pages=training_pages)
    process_book('SongBook_BossaNova_3', 6, training_pages=training_pages)
    process_book('SongBook_BossaNova_4', 5, training_pages=training_pages)
    process_book('SongBook_BossaNova_5', 5, 136, training_pages=training_pages)
    if correct_songs_with_llm:
        correct_songs()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--correct-songs-with-llm",
        action="store_true",
        help="Use the OpenAI API to write src/music/corrected_songs.csv after songs.csv is generated.",
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(correct_songs_with_llm=args.correct_songs_with_llm)
