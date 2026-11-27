from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from engine.ClassificationEngine import ClassificationEngine
from main import get_default_training_pages


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
MUSIC_DIR = SCRIPT_DIR / "music"
CONFIG_PATH = SCRIPT_DIR / "data" / "local_songbooks.json"
TITLE_PAGE = 0
EXCLUDED_PAGE = 2


@dataclass(frozen=True)
class BookConfig:
    name: str
    title: str
    preamble: int = 0
    max_pages: int | None = None
    expected_song_count: int | None = None
    known_blockers: list[str] | None = None
    manual_start_pages: list[int] | None = None
    page_overrides: dict[str, dict[str, str]] | None = None
    excluded_pages: list[int] | None = None
    review_status: str = "pending"
    review_notes: str = ""
    allowed_one_page_starts: list[int] | None = None
    reviewed_titles: list[str] | None = None
    reviewed_artists: list[str] | None = None
    allowed_long_starts: list[int] | None = None


@dataclass(frozen=True)
class SongBoundary:
    song_index: int
    start_index: int
    end_index: int

    @property
    def page_count(self) -> int:
        return self.end_index - self.start_index


def load_books(path: Path = CONFIG_PATH) -> list[BookConfig]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [BookConfig(**item) for item in data["books"]]


def build_boundaries(labels: list[int]) -> list[SongBoundary]:
    boundaries: list[SongBoundary] = []
    current_start: int | None = None
    song_index = 1

    for page_index, label in enumerate(labels):
        if label == EXCLUDED_PAGE:
            if current_start is not None:
                boundaries.append(
                    SongBoundary(song_index, current_start, page_index)
                )
                song_index += 1
                current_start = None
            continue

        if label == TITLE_PAGE:
            if current_start is not None:
                boundaries.append(
                    SongBoundary(song_index, current_start, page_index)
                )
                song_index += 1
            current_start = page_index

    if current_start is not None:
        boundaries.append(SongBoundary(song_index, current_start, len(labels)))
    return boundaries


def safe_filename(value: str, fallback: str) -> str:
    value = re.sub(r"[^\w\s.-]", "", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    return value[:100] or fallback


def page_texts(reader: PdfReader) -> list[str]:
    texts: list[str] = []
    for page in reader.pages:
        try:
            texts.append((page.extract_text() or "").strip())
        except Exception:
            texts.append("")
    return texts


def repeated_text_ratio(texts: list[str]) -> float:
    normalized = [re.sub(r"\s+", " ", text).strip().casefold() for text in texts]
    meaningful = [text for text in normalized if len(text) >= 20]
    if not meaningful:
        return 0.0
    return Counter(meaningful).most_common(1)[0][1] / len(meaningful)


def validate_manual_start_pages(config: BookConfig, page_count: int) -> None:
    pages = config.manual_start_pages
    if not pages:
        return
    if pages != sorted(set(pages)):
        raise ValueError(
            f"{config.name} manual start pages must be unique and ascending"
        )
    first_allowed = config.preamble + 1
    last_allowed = config.max_pages or page_count
    outside = [page for page in pages if not first_allowed <= page <= last_allowed]
    if outside:
        raise ValueError(
            f"{config.name} manual start pages outside {first_allowed}-{last_allowed}: "
            + ", ".join(map(str, outside))
        )
    if (
        config.expected_song_count is not None
        and len(pages) != config.expected_song_count
    ):
        raise ValueError(
            f"{config.name} has {len(pages)} reviewed starts but expects "
            f"{config.expected_song_count} songs"
        )
    if config.reviewed_titles is not None and len(config.reviewed_titles) != len(pages):
        raise ValueError(
            f"{config.name} has {len(config.reviewed_titles)} reviewed titles but "
            f"{len(pages)} reviewed starts"
        )
    if config.reviewed_artists is not None and len(config.reviewed_artists) != len(pages):
        raise ValueError(
            f"{config.name} has {len(config.reviewed_artists)} reviewed artists but "
            f"{len(pages)} reviewed starts"
        )
    excluded = config.excluded_pages or []
    if excluded != sorted(set(excluded)):
        raise ValueError(f"{config.name} excluded pages must be unique and ascending")
    overlap = sorted(set(pages) & set(excluded))
    if overlap:
        raise ValueError(
            f"{config.name} pages cannot be both song starts and excluded: "
            + ", ".join(map(str, overlap))
        )
    excluded_outside = [
        page for page in excluded if not first_allowed <= page <= last_allowed
    ]
    if excluded_outside:
        raise ValueError(
            f"{config.name} excluded pages outside {first_allowed}-{last_allowed}: "
            + ", ".join(map(str, excluded_outside))
        )


def boundary_warnings(
    boundary: SongBoundary,
    page,
    text_lengths: list[int],
    preamble: int,
    *,
    metadata_reviewed: bool = False,
    allow_one_page: bool = False,
    allow_long: bool = False,
) -> list[str]:
    warnings: list[str] = []
    title = (page.title or "").strip()
    artist = (page.artist or "").strip()
    if not title:
        warnings.append("missing title")
    if not artist:
        warnings.append("missing artist")
    if boundary.page_count == 1 and not allow_one_page:
        warnings.append("one-page segment")
    if boundary.page_count > 6 and not allow_long:
        warnings.append(f"long segment ({boundary.page_count} pages)")
    absolute_start = preamble + boundary.start_index
    absolute_end = preamble + boundary.end_index
    if text_lengths[absolute_start] < 20:
        warnings.append("title page has little/no OCR text")
    if not metadata_reviewed:
        extraction = page.extraction
        if not extraction.plausible_title_page:
            warnings.append("weak title-page extraction")
        if extraction.rejection_reasons:
            warnings.append("extraction: " + ", ".join(extraction.rejection_reasons))
    return warnings


def write_split(
    reader: PdfReader,
    output_path: Path,
    start_page: int,
    end_page: int,
) -> None:
    writer = PdfWriter()
    for page_index in range(start_page, end_page):
        writer.add_page(reader.pages[page_index])
    with output_path.open("wb") as output:
        writer.write(output)


def prepare_book(
    config: BookConfig,
    batch_dir: Path,
    training_pages,
    *,
    write_pdfs: bool,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    source_path = MUSIC_DIR / f"{config.name}.pdf"
    ocr_path = MUSIC_DIR / f"ocr_{config.name}.pdf"
    if not source_path.exists():
        raise FileNotFoundError(f"Missing source PDF: {source_path}")
    if not ocr_path.exists():
        raise FileNotFoundError(f"Missing OCR PDF: {ocr_path}")

    source_reader = PdfReader(source_path)
    ocr_reader = PdfReader(ocr_path)
    validate_manual_start_pages(config, len(ocr_reader.pages))
    texts = page_texts(ocr_reader)
    text_lengths = [len(text) for text in texts]
    text_pages = sum(length >= 20 for length in text_lengths)
    coverage = text_pages / len(text_lengths) if text_lengths else 0.0
    blockers: list[str] = list(config.known_blockers or [])
    if not config.manual_start_pages:
        blockers.append(
            "song boundaries have not been reconciled with the book contents"
        )
    if len(source_reader.pages) != len(ocr_reader.pages):
        blockers.append(
            f"source/OCR page mismatch ({len(source_reader.pages)} vs {len(ocr_reader.pages)})"
        )
    if coverage < 0.5:
        blockers.append(f"OCR coverage below 50% ({coverage:.1%})")
    repeated_ratio = repeated_text_ratio(texts)
    if repeated_ratio >= 0.5:
        blockers.append(
            f"same OCR text repeated on {repeated_ratio:.1%} of text-bearing pages"
        )

    cache_path = PROJECT_DIR / "pickled" / f"extracted_{config.name}" / "full_document.pickle"
    refresh_cache = not cache_path.exists() or ocr_path.stat().st_mtime > cache_path.stat().st_mtime
    engine = ClassificationEngine(config.name)
    engine.set_pages_from_file(
        str(ocr_path),
        preamble=config.preamble,
        max_pages=config.max_pages or 2**1000,
        redo=refresh_cache,
        training_pages=training_pages,
    )
    engine.classifier.train()
    if config.manual_start_pages:
        labels = [1] * len(engine.pages)
        for source_page in config.manual_start_pages:
            relative_index = source_page - config.preamble - 1
            if relative_index < 0 or relative_index >= len(labels):
                raise ValueError(
                    f"Configured start page {source_page} is outside {config.name}'s page window"
                )
            labels[relative_index] = TITLE_PAGE
        for source_page in config.excluded_pages or []:
            relative_index = source_page - config.preamble - 1
            if relative_index < 0 or relative_index >= len(labels):
                raise ValueError(
                    f"Configured excluded page {source_page} is outside {config.name}'s page window"
                )
            labels[relative_index] = EXCLUDED_PAGE
    else:
        labels = engine.classifier.label_pages()

    for source_page, title in zip(
        config.manual_start_pages or [], config.reviewed_titles or []
    ):
        relative_index = source_page - config.preamble - 1
        engine.pages[relative_index].title = title
    for source_page, artist in zip(
        config.manual_start_pages or [], config.reviewed_artists or []
    ):
        relative_index = source_page - config.preamble - 1
        engine.pages[relative_index].artist = artist

    for source_page_text, override in (config.page_overrides or {}).items():
        relative_index = int(source_page_text) - config.preamble - 1
        if relative_index < 0 or relative_index >= len(engine.pages):
            raise ValueError(
                f"Configured page override {source_page_text} is outside {config.name}'s page window"
            )
        page = engine.pages[relative_index]
        page.title = override.get("title", page.title)
        page.artist = override.get("artist", page.artist)
    boundaries = build_boundaries(labels)
    if not boundaries:
        blockers.append("classifier found no songs")
    if (
        config.expected_song_count is not None
        and len(boundaries) != config.expected_song_count
    ):
        blockers.append(
            f"expected {config.expected_song_count} songs, found {len(boundaries)}"
        )

    book_dir = batch_dir / config.name
    split_dir = book_dir / "split"
    split_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for boundary in boundaries:
        page = engine.pages[boundary.start_index]
        title = (page.title or "").strip()
        artist = (page.artist or "").strip()
        source_start = config.preamble + boundary.start_index
        source_end = config.preamble + boundary.end_index
        filename = (
            f"{boundary.song_index:03d}-p{source_start + 1:03d}-"
            f"{safe_filename(title, 'MISSING_TITLE')}-"
            f"{safe_filename(artist, 'MISSING_ARTIST')}.pdf"
        )
        source_start_page = source_start + 1
        warnings = boundary_warnings(
            boundary,
            page,
            text_lengths,
            config.preamble,
            metadata_reviewed=bool(config.reviewed_titles or config.reviewed_artists)
            or str(source_start_page) in (config.page_overrides or {}),
            allow_one_page=source_start_page in (config.allowed_one_page_starts or []),
            allow_long=source_start_page in (config.allowed_long_starts or []),
        )
        if write_pdfs:
            write_split(
                ocr_reader,
                split_dir / filename,
                source_start,
                source_end,
            )
        rows.append(
            {
                "book_name": config.name,
                "book_title": config.title,
                "song_index": boundary.song_index,
                "source_start_page": source_start + 1,
                "source_end_page": source_end,
                "page_count": boundary.page_count,
                "title": title,
                "artist": artist,
                "file": f"{config.name}/split/{filename}",
                "automated_status": "REVIEW" if warnings else "CHECK",
                "warnings": " | ".join(warnings),
                "review_decision": "",
                "review_notes": "",
            }
        )

    leading_pages = boundaries[0].start_index if boundaries else len(labels)
    flagged = sum(row["automated_status"] == "REVIEW" for row in rows)
    return (
        {
            "name": config.name,
            "title": config.title,
            "source_pages": len(source_reader.pages),
            "ocr_pages": len(ocr_reader.pages),
            "ocr_coverage": coverage,
            "songs": len(boundaries),
            "flagged": flagged,
            "leading_pages": leading_pages,
            "boundary_source": (
                "contents-reconciled" if config.manual_start_pages else "classifier"
            ),
            "review_status": config.review_status,
            "review_notes": config.review_notes,
            "blockers": blockers,
        },
        rows,
    )


def write_review_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = list(rows[0]) if rows else [
        "book_name",
        "book_title",
        "song_index",
        "source_start_page",
        "source_end_page",
        "page_count",
        "title",
        "artist",
        "file",
        "automated_status",
        "warnings",
        "review_decision",
        "review_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_index(
    path: Path,
    summaries: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> None:
    batch_ready = bool(summaries) and all(
        summary["review_status"] in {"approved", "ready"}
        and not summary["blockers"]
        and summary["flagged"] == 0
        for summary in summaries
    )
    readiness_text = (
        "This batch is **deployment-ready**: every book is contents-reconciled "
        "and there are no unresolved automated warnings or blockers."
        if batch_ready
        else "The batch is **not deployment-ready** until all blockers are resolved. "
        "Contents-reconciled books need a representative spot check; classifier-only "
        "books require full boundary review."
    )
    lines = [
        "# Local songbook preparation review",
        "",
        "No files in this report have been uploaded or deployed.",
        readiness_text,
        "",
        "| Book | Review status | Boundary source | OCR coverage | Songs | Flagged | Leading pages | Blockers |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for summary in summaries:
        blockers = "; ".join(summary["blockers"]) or "—"
        lines.append(
            f"| {summary['title']} | {summary['review_status']} | "
            f"{summary['boundary_source']} | "
            f"{summary['ocr_coverage']:.1%} | "
            f"{summary['songs']} | {summary['flagged']} | "
            f"{summary['leading_pages']} | {blockers} |"
        )
    lines.extend(["", "## Splits requiring attention", ""])
    flagged_rows = [row for row in rows if row["automated_status"] == "REVIEW"]
    if not flagged_rows:
        lines.append(
            "No unresolved automated warnings."
            if batch_ready
            else "No automated warnings. Pending books still require the review described below."
        )
    for row in flagged_rows:
        lines.append(
            f"- [{row['book_title']} #{row['song_index']}: "
            f"{row['title'] or 'MISSING TITLE'}]({row['file']}) — {row['warnings']}"
        )
    lines.extend(
        [
            "",
            "## Review instructions",
            "",
            (
                "No further boundary review is required for this batch. Retain `review.csv` as the audit record."
                if batch_ready
                else "For a contents-reconciled book, spot-check the first, last, longest, and several random PDFs. For a classifier-only book, inspect every boundary. Record any rejected split or OCR/name problem in `review.csv`."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare local-only songbooks in an isolated, reviewable batch."
    )
    parser.add_argument("--books", nargs="*", help="Book names from local_songbooks.json")
    parser.add_argument("--output", type=Path, help="Output directory (defaults under reports/)")
    parser.add_argument(
        "--no-pdfs",
        action="store_true",
        help="Generate diagnostics without writing split PDFs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    books = load_books()
    if args.books:
        wanted = set(args.books)
        books = [book for book in books if book.name in wanted]
        missing = wanted - {book.name for book in books}
        if missing:
            raise ValueError(f"Unknown configured books: {', '.join(sorted(missing))}")
    batch_dir = args.output or (
        PROJECT_DIR / "reports" / f"local_preparation_{datetime.now():%Y%m%d_%H%M%S}"
    )
    batch_dir.mkdir(parents=True, exist_ok=True)
    training_pages = get_default_training_pages(["por", "eng"])
    summaries: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for config in books:
        print(f"Preparing {config.title}...")
        summary, book_rows = prepare_book(
            config,
            batch_dir,
            training_pages,
            write_pdfs=not args.no_pdfs,
        )
        summaries.append(summary)
        rows.extend(book_rows)
    write_review_csv(batch_dir / "review.csv", rows)
    write_index(batch_dir / "index.md", summaries, rows)
    print(f"Prepared {len(rows)} candidate songs from {len(summaries)} books.")
    print(f"Review report: {batch_dir / 'index.md'}")
    batch_ready = bool(summaries) and all(
        summary["review_status"] in {"approved", "ready"}
        and not summary["blockers"]
        and summary["flagged"] == 0
        for summary in summaries
    )
    print(
        "Status: READY FOR STAGING"
        if batch_ready
        else "Status: NOT READY FOR DEPLOYMENT (review/blockers remain)"
    )


if __name__ == "__main__":
    main()
