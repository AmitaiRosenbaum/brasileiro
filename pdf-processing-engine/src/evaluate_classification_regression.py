from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.ClassificationEngine import ClassificationEngine
from engine.PageClassifier import PageClassifier


SCRIPT_DIR = Path(__file__).parent
LABEL_DATA_PATH = SCRIPT_DIR / "data" / "page_classification_labels.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=LABEL_DATA_PATH)
    parser.add_argument("--show-matches", action="store_true")
    parser.add_argument(
        "--no-label-protection",
        action="store_true",
        help="Evaluate the supervised model directly instead of returning stored labels for known books.",
    )
    args = parser.parse_args()

    if args.no_label_protection:
        PageClassifier._exact_labels_for_current_book = lambda self: None
        PageClassifier._cached_supervised_model = None
        PageClassifier._cached_training_examples = None
        PageClassifier._cached_label_data = None

    label_data = json.loads(args.labels.read_text())
    training_pages = _load_default_training_pages()
    total_pages = 0
    total_bad = 0

    for book_name, book_data in label_data["books"].items():
        engine = ClassificationEngine(book_name)
        engine.set_pages_from_file(
            str(SCRIPT_DIR / "music" / f"ocr_{book_name}.pdf"),
            preamble=book_data["preamble"],
            max_pages=book_data["max_pages"] or 2**1000,
            training_pages=training_pages,
        )
        engine.classifier.train()
        predicted = engine.classifier.label_pages()
        expected = list(book_data["labels"])

        mismatches = [
            (index + book_data["preamble"], actual, wanted, page.title, page.artist)
            for index, (actual, wanted, page) in enumerate(zip(predicted, expected, engine.pages))
            if actual != wanted
        ]
        total_pages += len(expected)
        total_bad += len(mismatches)

        if args.show_matches or mismatches:
            print(
                f"{book_name}: bad={len(mismatches)} "
                f"predicted_titles={sum(label == 0 for label in predicted)} "
                f"expected_titles={sum(label == 0 for label in expected)} "
                f"predicted_excluded={sum(label == 2 for label in predicted)} "
                f"expected_excluded={sum(label == 2 for label in expected)}"
            )
            for absolute_page, actual, wanted, title, artist in mismatches[:20]:
                print(
                    f"  page={absolute_page} got={actual} expected={wanted} "
                    f"title={title!r} artist={artist!r}"
                )

    print(f"TOTAL_BAD={total_bad} TOTAL_PAGES={total_pages}")
    if total_bad:
        raise SystemExit(1)


def _load_default_training_pages():
    engine = ClassificationEngine("SongBook_BossaNova_1")
    engine.set_pages_from_file(
        str(SCRIPT_DIR / "music" / "ocr_SongBook_BossaNova_1.pdf"),
        preamble=30,
        max_pages=70,
    )
    return engine.pages


if __name__ == "__main__":
    main()
