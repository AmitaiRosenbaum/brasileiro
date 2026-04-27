from __future__ import annotations

import argparse
import csv
from difflib import SequenceMatcher
from pathlib import Path
import re

from engine.ClassificationEngine import ClassificationEngine
from engine.PageClassifier import TITLE_PAGE


SCRIPT_DIR = Path(__file__).parent
DEFAULT_LABELS = SCRIPT_DIR.parent / "public" / "manual_classifications.txt"
DEFAULT_CORRECTED_SONGS = SCRIPT_DIR / "data" / "corrected_songs.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book_name", nargs="?", default="SongBook_BossaNova_1")
    parser.add_argument("--preamble", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=70)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--corrected-songs", type=Path, default=DEFAULT_CORRECTED_SONGS)
    parser.add_argument("--redo", action="store_true")
    args = parser.parse_args()

    engine = ClassificationEngine(args.book_name)
    pdf_path = SCRIPT_DIR / "music" / f"ocr_{args.book_name}.pdf"
    engine.set_pages_from_file(
        str(pdf_path),
        preamble=args.preamble,
        max_pages=args.max_pages,
        redo=args.redo,
    )

    if args.labels.exists():
        engine.classifier._labels = _read_labels(args.labels)

    engine.classifier.train()
    classification = engine.classifier.evaluate_training_labels()
    labels = engine.classifier.label_pages()
    title_pages = [page for page, label in zip(engine.pages, labels) if label == TITLE_PAGE]
    expected = _read_corrected_songs(args.corrected_songs)[: len(title_pages)]

    print("Classification")
    print(f"  accuracy: {classification.accuracy:.3f}")
    print(f"  false positives: {classification.false_positive}")
    print(f"  false negatives: {classification.false_negative}")
    print()
    print("Extraction")
    for index, (page, song) in enumerate(zip(title_pages, expected)):
        title_score = _similarity(page.title, song["title"])
        artist_score = _similarity(page.artist, song["artist"])
        marker = "OK" if title_score >= 0.75 and artist_score >= 0.75 else "CHECK"
        print(
            f"  {marker} #{index:03d} page={page.index:03d} "
            f"title={title_score:.2f} artist={artist_score:.2f} "
            f"got=({page.title!r}; {page.artist!r}) "
            f"expected=({song['title']!r}; {song['artist']!r})"
        )


def _read_labels(path: Path) -> list[int]:
    labels: list[int] = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and set(stripped) <= {"0", "1"}:
            labels.extend(int(char) for char in stripped)
    return labels


def _read_corrected_songs(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        songs = []
        for row in reader:
            normalized = {key.strip(): value.strip() for key, value in row.items()}
            songs.append(
                {
                    "artist": normalized["artist"],
                    "title": normalized["title"],
                }
            )
        return songs


def _similarity(value: str | None, expected: str) -> float:
    return SequenceMatcher(None, _normalize(value or ""), _normalize(expected)).ratio()


def _normalize(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9À-ÿ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    main()
