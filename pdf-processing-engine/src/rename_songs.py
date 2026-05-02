from __future__ import annotations

import argparse
import csv
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
SPLIT_DIR = SCRIPT_DIR / "music" / "split"
FINAL_DIR = SCRIPT_DIR / "music" / "final"
CORRECTED_SONGS_CSV = SCRIPT_DIR / "music" / "corrected_songs.csv"
RENAMING_FILES_CSV = SCRIPT_DIR / "music" / "renaming_files.csv"
MANIFEST_CSV = FINAL_DIR / "manifest.csv"

MISSING_VALUE_RE = re.compile(r"MISSING_(?:TITLE|ARTIST)(?:_|$|\b)", re.IGNORECASE)


@dataclass(frozen=True)
class CorrectedSong:
    index: int
    artist: str
    title: str


@dataclass(frozen=True)
class RenamedSong:
    index: int
    source_file: str
    final_file: str
    title: str
    artist: str
    version: int
    song_key: str
    title_slug: str
    artist_slug: str


def strip_diacritics(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def slugify(value: str, fallback: str) -> str:
    normalized = strip_diacritics(value).casefold()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or fallback


def normalized_identity(value: str) -> str:
    normalized = strip_diacritics(value).casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def split_sort_key(path: Path) -> int:
    match = re.match(r"^(\d+)-", path.name)
    if not match:
        raise ValueError(f"Split PDF does not start with a numeric index: {path.name}")
    return int(match.group(1))


def read_split_files(split_dir: Path) -> list[Path]:
    files = sorted(split_dir.glob("*.pdf"), key=split_sort_key)
    if not files:
        raise FileNotFoundError(f"No split PDFs found in {split_dir}")
    return files


def read_corrected_songs(path: Path) -> list[CorrectedSong]:
    if not path.exists():
        raise FileNotFoundError(f"Missing corrected songs CSV: {path}")

    songs: list[CorrectedSong] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        expected_fields = {"artist", "title"}
        actual_fields = set(reader.fieldnames or [])
        if not expected_fields.issubset(actual_fields):
            raise ValueError(
                f"{path} must contain ';'-separated artist and title columns"
            )

        for index, row in enumerate(reader):
            songs.append(
                CorrectedSong(
                    index=index,
                    artist=(row.get("artist") or "").strip(),
                    title=(row.get("title") or "").strip(),
                )
            )

    if not songs:
        raise ValueError(f"No songs found in {path}")
    return songs


def build_renamed_songs(
    split_files: list[Path],
    corrected_songs: list[CorrectedSong],
) -> tuple[list[RenamedSong], list[str]]:
    if len(split_files) != len(corrected_songs):
        raise ValueError(
            "Split PDF count does not match corrected_songs.csv rows: "
            f"{len(split_files)} split PDFs vs {len(corrected_songs)} corrected rows"
        )

    identity_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    renamed_songs: list[RenamedSong] = []
    warnings: list[str] = []

    for split_file, song in zip(split_files, corrected_songs, strict=True):
        title_slug = slugify(song.title, f"missing-title-{song.index:03d}")
        artist_slug = slugify(song.artist, f"missing-artist-{song.index:03d}")
        identity = (
            normalized_identity(song.title),
            normalized_identity(song.artist),
        )
        identity_counts[identity] += 1
        version = identity_counts[identity]
        song_key = f"{title_slug}__{artist_slug}"
        final_file = f"{song_key}__v{version:02d}.pdf"

        if _needs_manual_name(song.title) or _needs_manual_name(song.artist):
            warnings.append(
                "manual name needed: "
                f"row {song.index + 1}, source={split_file.name}, "
                f"artist={song.artist!r}, title={song.title!r}"
            )

        renamed_songs.append(
            RenamedSong(
                index=song.index,
                source_file=split_file.name,
                final_file=final_file,
                title=song.title,
                artist=song.artist,
                version=version,
                song_key=song_key,
                title_slug=title_slug,
                artist_slug=artist_slug,
            )
        )

    return renamed_songs, warnings


def _needs_manual_name(value: str) -> bool:
    return not value.strip() or bool(MISSING_VALUE_RE.search(value))


def write_renaming_files(split_files: list[Path], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["title", "artist", "source_file"])
        for split_file in split_files:
            name_without_extension = re.sub(r"^\d+-", "", split_file.stem)
            title, separator, artist = name_without_extension.rpartition("-")
            if not separator:
                title = name_without_extension
                artist = ""
            writer.writerow([title, artist, split_file.name])


def write_manifest(renamed_songs: list[RenamedSong], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "index",
                "source_file",
                "final_file",
                "title",
                "artist",
                "version",
                "song_key",
                "title_slug",
                "artist_slug",
            ]
        )
        for song in renamed_songs:
            writer.writerow(
                [
                    song.index,
                    song.source_file,
                    song.final_file,
                    song.title,
                    song.artist,
                    song.version,
                    song.song_key,
                    song.title_slug,
                    song.artist_slug,
                ]
            )


def copy_final_files(
    split_dir: Path,
    final_dir: Path,
    renamed_songs: list[RenamedSong],
    *,
    clean: bool,
    dry_run: bool,
) -> None:
    final_dir.mkdir(parents=True, exist_ok=True)
    existing_pdfs = sorted(final_dir.glob("*.pdf"))

    if existing_pdfs and clean and not dry_run:
        for path in existing_pdfs:
            path.unlink()
    elif existing_pdfs and not clean:
        print(
            "WARNING: final directory already contains PDFs. "
            "Run with --clean to remove stale final PDFs before copying."
        )

    for song in renamed_songs:
        source_path = split_dir / song.source_file
        destination_path = final_dir / song.final_file
        if dry_run:
            print(f"DRY RUN: {source_path.name} -> {destination_path.name}")
            continue
        shutil.copy2(source_path, destination_path)


def print_warnings(warnings: list[str]) -> None:
    if not warnings:
        return

    print("")
    print("WARNING: manual naming required before upload")
    for warning in warnings:
        print(f"- {warning}")


def print_version_summary(renamed_songs: list[RenamedSong]) -> None:
    versioned_songs = [song for song in renamed_songs if song.version > 1]
    if not versioned_songs:
        return

    print("")
    print("Versioned songs")
    for song in versioned_songs:
        print(
            f"- v{song.version:02d}: {song.title} - {song.artist} "
            f"({song.final_file})"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy split PDFs to music/final with versioned, B2-safe filenames "
            "and write a manifest for API ingestion."
        )
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing PDFs in music/final before copying renamed files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned copies without writing PDFs or manifest.csv.",
    )
    parser.add_argument(
        "--write-renaming-files",
        action="store_true",
        help="Regenerate music/renaming_files.csv from the current split PDFs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    split_files = read_split_files(SPLIT_DIR)

    if args.write_renaming_files and not args.dry_run:
        write_renaming_files(split_files, RENAMING_FILES_CSV)

    corrected_songs = read_corrected_songs(CORRECTED_SONGS_CSV)
    renamed_songs, warnings = build_renamed_songs(split_files, corrected_songs)

    copy_final_files(
        SPLIT_DIR,
        FINAL_DIR,
        renamed_songs,
        clean=args.clean,
        dry_run=args.dry_run,
    )
    if not args.dry_run:
        write_manifest(renamed_songs, MANIFEST_CSV)

    duplicate_count = sum(1 for song in renamed_songs if song.version > 1)
    print(
        f"Prepared {len(renamed_songs)} final PDFs "
        f"({duplicate_count} additional versions)."
    )
    if not args.dry_run:
        print(f"Wrote manifest: {MANIFEST_CSV}")
    print_version_summary(renamed_songs)
    print_warnings(warnings)


if __name__ == "__main__":
    main()
