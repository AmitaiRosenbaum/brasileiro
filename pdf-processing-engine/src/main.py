
import argparse
import os
import tempfile
from pathlib import Path
from engine.ClassificationEngine import ClassificationEngine
from correct_songs_with_llm import correct_songs


SCRIPT_DIR = Path(__file__).parent
DEFAULT_OCR_LANGUAGES = ("por",)


def _normalize_book_name(book_name: str) -> str:
    return Path(book_name).stem


def _get_book_paths(book_name: str) -> tuple[str, Path, Path]:
    normalized_book_name = _normalize_book_name(book_name)
    original_file_path = SCRIPT_DIR / "music" / f"{normalized_book_name}.pdf"
    ocr_file_path = SCRIPT_DIR / "music" / f"ocr_{normalized_book_name}.pdf"
    return normalized_book_name, original_file_path, ocr_file_path


def _parse_ocr_languages(raw_value: str | None) -> list[str]:
    value = raw_value or os.environ.get("OCR_LANGUAGES") or "+".join(DEFAULT_OCR_LANGUAGES)
    languages = [
        language.strip()
        for language in value.replace(",", "+").split("+")
        if language.strip()
    ]
    if not languages:
        raise ValueError("OCR language list cannot be empty")
    return languages


def _format_ocr_languages(languages: list[str]) -> str:
    return "+".join(languages)


def _ensure_ocr_pdf(
    book_name: str,
    ocr_languages: list[str],
    redo_ocr: bool = False,
) -> tuple[str, Path]:
    normalized_book_name, original_file_path, ocr_file_path = _get_book_paths(book_name)

    if redo_ocr or not ocr_file_path.exists():
        if not original_file_path.exists():
            raise FileNotFoundError(
                f"Could not find source PDF for {normalized_book_name}: {original_file_path}"
            )

        action = "Refreshing" if redo_ocr and ocr_file_path.exists() else "Adding"
        print(
            f"{action} OCR layer for {normalized_book_name} "
            f"using languages={_format_ocr_languages(ocr_languages)}"
        )

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=ocr_file_path.parent,
            delete=False,
        ) as temp_file:
            temp_output_path = Path(temp_file.name)

        try:
            ClassificationEngine(normalized_book_name).ocr(
                str(original_file_path),
                str(temp_output_path),
                languages=ocr_languages,
            )
            temp_output_path.replace(ocr_file_path)
        finally:
            if temp_output_path.exists():
                temp_output_path.unlink()

    return normalized_book_name, ocr_file_path


def get_default_training_pages(
    ocr_languages: list[str],
    redo_ocr: bool = False,
):
    book_name, ocr_file_path = _ensure_ocr_pdf(
        "SongBook_BossaNova_1",
        ocr_languages=ocr_languages,
        redo_ocr=redo_ocr,
    )
    engine = ClassificationEngine(book_name)
    engine.set_pages_from_file(
        str(ocr_file_path),
        preamble=30,
        max_pages=70,
        redo=redo_ocr,
    )
    return engine.pages


def process_book(
    book_name: str,
    preamble: int,
    max_pages: int = 2**1000,
    training_pages=None,
    ocr_languages: list[str] | None = None,
    redo_ocr: bool = False,
):
    normalized_book_name, ocr_file_path = _ensure_ocr_pdf(
        book_name,
        ocr_languages=ocr_languages or list(DEFAULT_OCR_LANGUAGES),
        redo_ocr=redo_ocr,
    )
    print(f"Starting {normalized_book_name}")
    engine = ClassificationEngine(normalized_book_name)

    # Set engine's pages
    engine.set_pages_from_file(
        str(ocr_file_path),
        preamble=preamble,
        max_pages=max_pages,
        redo=redo_ocr,
        training_pages=training_pages,
    )

    engine.classifier.train()

    engine.classify_pages()

    for page in engine.pages:
        if not page.type:
            print(page.index, page.title, page.artist)

    engine.transformer.split(
        str(ocr_file_path), SCRIPT_DIR / 'music' / 'split', skip=preamble)


def main(
    correct_songs_with_llm: bool = False,
    ocr_languages: list[str] | None = None,
    redo_ocr: bool = False,
):
    ocr_languages = ocr_languages or list(DEFAULT_OCR_LANGUAGES)
    training_pages = get_default_training_pages(
        ocr_languages=ocr_languages,
        redo_ocr=redo_ocr,
    )
    process_book(
        'Chico_Buarque_1.pdf',
        31,
        215,
        training_pages=training_pages,
        ocr_languages=ocr_languages,
        redo_ocr=redo_ocr,
    )
    process_book(
        'Chico_Buarque_2.pdf',
        34,
        training_pages=training_pages,
        ocr_languages=ocr_languages,
        redo_ocr=redo_ocr,
    )
    process_book(
        'Chico_Buarque_3.pdf',
        31,
        training_pages=training_pages,
        ocr_languages=ocr_languages,
        redo_ocr=redo_ocr,
    )
    process_book(
        'Chico_Buarque_4.pdf',
        28,
        training_pages=training_pages,
        ocr_languages=ocr_languages,
        redo_ocr=redo_ocr,
    )
    if correct_songs_with_llm:
        correct_songs()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--correct-songs-with-llm",
        action="store_true",
        help="Use the OpenAI API to write src/music/corrected_songs.csv after songs.csv is generated.",
    )
    parser.add_argument(
        "--ocr-languages",
        default=None,
        help=(
            "OCR language codes for Tesseract, for example 'por' or 'por+eng'. "
            "Defaults to OCR_LANGUAGES or 'por'."
        ),
    )
    parser.add_argument(
        "--redo-ocr",
        action="store_true",
        help="Regenerate existing OCR PDFs and refresh cached PDFMiner extraction.",
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(
        correct_songs_with_llm=args.correct_songs_with_llm,
        ocr_languages=_parse_ocr_languages(args.ocr_languages),
        redo_ocr=args.redo_ocr,
    )
