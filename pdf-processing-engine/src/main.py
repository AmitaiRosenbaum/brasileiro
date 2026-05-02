
import argparse
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine
from correct_songs_with_llm import correct_songs


SCRIPT_DIR = Path(__file__).parent


def _normalize_book_name(book_name: str) -> str:
    return Path(book_name).stem


def _get_book_paths(book_name: str) -> tuple[str, Path, Path]:
    normalized_book_name = _normalize_book_name(book_name)
    original_file_path = SCRIPT_DIR / "music" / f"{normalized_book_name}.pdf"
    ocr_file_path = SCRIPT_DIR / "music" / f"ocr_{normalized_book_name}.pdf"
    return normalized_book_name, original_file_path, ocr_file_path


def _ensure_ocr_pdf(book_name: str) -> tuple[str, Path]:
    normalized_book_name, original_file_path, ocr_file_path = _get_book_paths(book_name)

    if not ocr_file_path.exists():
        if not original_file_path.exists():
            raise FileNotFoundError(
                f"Could not find source PDF for {normalized_book_name}: {original_file_path}"
            )

        print(f"Adding OCR layer for {normalized_book_name}")
        ClassificationEngine(normalized_book_name).ocr(
            str(original_file_path),
            str(ocr_file_path),
        )

    return normalized_book_name, ocr_file_path


def get_default_training_pages():
    book_name, ocr_file_path = _ensure_ocr_pdf("SongBook_BossaNova_1")
    engine = ClassificationEngine(book_name)
    engine.set_pages_from_file(str(ocr_file_path), preamble=30, max_pages=70)
    return engine.pages


def process_book(
    book_name: str,
    preamble: int,
    max_pages: int = 2**1000,
    training_pages=None,
):
    normalized_book_name, ocr_file_path = _ensure_ocr_pdf(book_name)
    print(f"Starting {normalized_book_name}")
    engine = ClassificationEngine(normalized_book_name)

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
        str(ocr_file_path), SCRIPT_DIR / 'music' / 'split', skip=preamble)


def main(correct_songs_with_llm: bool = False):
    training_pages = get_default_training_pages()
    process_book('Chico_Buarque_1.pdf', 31, 215, training_pages=training_pages)
    process_book('Chico_Buarque_2.pdf', 34, training_pages=training_pages)
    process_book('Chico_Buarque_3.pdf', 31, training_pages=training_pages)
    process_book('Chico_Buarque_4.pdf', 28, training_pages=training_pages)
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
