from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_DIR / "reports" / "manifest_with_book_sections.csv"
DEFAULT_OUTPUT = PROJECT_DIR / "reports" / "b2_manifest_with_books.csv"
BOOK_MARKER_RE = re.compile(r"^NEW BOOK STARTING HERE\.\s*TITLE:\s*(.+)$", re.IGNORECASE)
DUPLICATE_BOOK_RENAMES = {
    ("Gilberto Gil I", 2): "Gilberto Gil II",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a manifest annotated with NEW BOOK STARTING HERE markers "
            "into a normal CSV manifest with book_title and book_song_index fields."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def normalized_book_title(title: str, seen_counts: Counter[str]) -> str:
    seen_counts[title] += 1
    return DUPLICATE_BOOK_RENAMES.get((title, seen_counts[title]), title)


def convert_manifest(input_path: Path, output_path: Path) -> tuple[int, int]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        header_line = input_file.readline()
        if not header_line:
            raise ValueError(f"{input_path} is empty")

        header = next(csv.reader([header_line]))
        output_header = [
            *header[:5],
            "book_title",
            "book_song_index",
            *header[5:],
        ]

        rows = []
        current_book_title = ""
        current_book_index = 0
        book_sections = 0
        seen_book_titles: Counter[str] = Counter()

        for line_number, raw_line in enumerate(input_file, start=2):
            stripped_line = raw_line.strip()
            if not stripped_line:
                continue

            marker_match = BOOK_MARKER_RE.match(stripped_line)
            if marker_match:
                marker_title = marker_match.group(1).strip()
                current_book_title = normalized_book_title(marker_title, seen_book_titles)
                current_book_index = 0
                book_sections += 1
                continue

            if not current_book_title:
                raise ValueError(
                    f"Song row appears before any book marker at line {line_number}"
                )

            row = next(csv.reader([raw_line]))
            if len(row) != len(header):
                raise ValueError(
                    f"Line {line_number} has {len(row)} fields; expected {len(header)}"
                )

            current_book_index += 1
            rows.append([
                *row[:5],
                current_book_title,
                str(current_book_index),
                *row[5:],
            ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(output_header)
        writer.writerows(rows)

    return len(rows), book_sections


def main() -> None:
    args = parse_args()
    row_count, book_section_count = convert_manifest(args.input, args.output)
    print(
        f"Wrote {row_count} rows across {book_section_count} book sections to {args.output}"
    )


if __name__ == "__main__":
    main()
