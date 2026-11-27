from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path

from normalization import (
    canonicalize_artist_text,
    canonicalize_title,
    normalized_identity,
)
from rename_songs import slugify


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "data" / "local_songbooks.json"


def load_ready_books() -> dict[str, dict[str, object]]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        book["name"]: book
        for book in data["books"]
        if book.get("review_status") in {"approved", "ready"}
    }


def read_audited_batches(batch_dirs: list[Path]) -> dict[str, tuple[Path, list[dict[str, str]]]]:
    selected: dict[str, tuple[Path, list[dict[str, str]]]] = {}
    for batch_dir in batch_dirs:
        review_path = batch_dir / "review.csv"
        if not review_path.exists():
            raise FileNotFoundError(f"Missing audit CSV: {review_path}")
        with review_path.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        by_book: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_book[row["book_name"]].append(row)
        for book_name, book_rows in by_book.items():
            selected[book_name] = (batch_dir, book_rows)
    return selected


def validate_selection(
    ready_books: dict[str, dict[str, object]],
    selected: dict[str, tuple[Path, list[dict[str, str]]]],
) -> None:
    missing_books = sorted(set(ready_books) - set(selected))
    if missing_books:
        raise ValueError(
            "Ready books missing from audited inputs: " + ", ".join(missing_books)
        )

    for book_name, config in ready_books.items():
        batch_dir, rows = selected[book_name]
        expected = int(config["expected_song_count"])
        reviewed_titles = config.get("reviewed_titles") or []
        reviewed_artists = config.get("reviewed_artists") or []
        if len(reviewed_titles) != expected or len(reviewed_artists) != expected:
            raise ValueError(
                f"{book_name}: metadata is not fully human-reviewed "
                f"({len(reviewed_titles)}/{expected} titles, "
                f"{len(reviewed_artists)}/{expected} artists). "
                "OCR output cannot be promoted directly to deployment staging."
            )
        if len(rows) != expected:
            raise ValueError(
                f"{book_name}: expected {expected} audited rows, found {len(rows)} "
                f"in {batch_dir}"
            )
        starts = [int(row["source_start_page"]) for row in rows]
        configured_starts = list(config["manual_start_pages"])
        if starts != configured_starts:
            raise ValueError(
                f"{book_name}: audited starts do not match the reviewed configuration"
            )
        indices = [int(row["song_index"]) for row in rows]
        if indices != list(range(1, expected + 1)):
            raise ValueError(f"{book_name}: song indices are not continuous")
        for row in rows:
            title = row["title"].strip()
            artist = row["artist"].strip()
            if not title or not artist or "MISSING_" in title or "MISSING_" in artist:
                raise ValueError(
                    f"{book_name} #{row['song_index']}: unresolved metadata"
                )
            row_index = int(row["song_index"]) - 1
            if title != str(reviewed_titles[row_index]).strip():
                raise ValueError(
                    f"{book_name} #{row['song_index']}: audited title does not match "
                    "the reviewed title"
                )
            if artist != str(reviewed_artists[row_index]).strip():
                raise ValueError(
                    f"{book_name} #{row['song_index']}: audited artist does not match "
                    "the reviewed artist"
                )
            source_pdf = batch_dir / row["file"]
            if not source_pdf.exists():
                raise FileNotFoundError(f"Missing audited PDF: {source_pdf}")


def build_staging(
    ready_books: dict[str, dict[str, object]],
    selected: dict[str, tuple[Path, list[dict[str, str]]]],
    output_dir: Path,
) -> int:
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to reuse staging directory: {output_dir}. Choose a new path."
        )
    output_dir.mkdir(parents=True)

    identity_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    manifest_rows: list[list[object]] = []
    catalog_index = 0

    for book_name, config in ready_books.items():
        batch_dir, rows = selected[book_name]
        for row in rows:
            title = canonicalize_title(row["title"].strip())
            artist = canonicalize_artist_text(row["artist"].strip())
            identity = (normalized_identity(title), normalized_identity(artist))
            identity_counts[identity] += 1
            version = identity_counts[identity]
            title_slug = slugify(title, f"missing-title-{catalog_index:03d}")
            artist_slug = slugify(artist, f"missing-artist-{catalog_index:03d}")
            song_key = f"{title_slug}__{artist_slug}"
            final_file = f"{song_key}__v{version:02d}.pdf"
            source_pdf = batch_dir / row["file"]
            destination = output_dir / final_file
            if destination.exists():
                raise ValueError(f"Duplicate staged filename: {final_file}")
            shutil.copy2(source_pdf, destination)
            manifest_rows.append(
                [
                    catalog_index,
                    f"{book_name}/{source_pdf.name}",
                    final_file,
                    title,
                    artist,
                    config["title"],
                    int(row["song_index"]),
                    version,
                    song_key,
                    title_slug,
                    artist_slug,
                ]
            )
            catalog_index += 1

    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            [
                "index",
                "source_file",
                "final_file",
                "title",
                "artist",
                "book_title",
                "book_song_index",
                "version",
                "song_key",
                "title_slug",
                "artist_slug",
            ]
        )
        writer.writerows(manifest_rows)
    return len(manifest_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an isolated B2 staging directory from audited songbook batches."
    )
    parser.add_argument("--batch", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ready_books = load_ready_books()
    selected = read_audited_batches([path.resolve() for path in args.batch])
    validate_selection(ready_books, selected)
    count = build_staging(ready_books, selected, args.output.resolve())
    expected = sum(int(book["expected_song_count"]) for book in ready_books.values())
    if count != expected:
        raise ValueError(f"Staged {count} PDFs but expected {expected}")
    print(f"Staged {count} audited PDFs from {len(ready_books)} books.")
    print(f"Manifest: {args.output.resolve() / 'manifest.csv'}")


if __name__ == "__main__":
    main()
