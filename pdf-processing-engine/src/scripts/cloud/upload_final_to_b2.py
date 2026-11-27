from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import boto3
from botocore.config import Config


SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parents[1]
PROJECT_DIR = SCRIPT_DIR.parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from normalization import canonicalize_artist_text, canonicalize_title, song_identity

DEFAULT_LOCAL_DIR = SRC_DIR / "music" / "final"
DEFAULT_MANIFEST = DEFAULT_LOCAL_DIR / "manifest.csv"
DEFAULT_BOOK_METADATA = SRC_DIR / "music" / "book_metadata.csv"
DEFAULT_BUCKET = "brasileiro"
DEFAULT_PREFIX = "brasileiro-songs"
DEFAULT_REGION = "us-east-005"
DEFAULT_REPORT = PROJECT_DIR / "reports" / "b2_upload_plan.csv"

LOGGER = logging.getLogger("upload_final_to_b2")
MISSING_VALUE_RE = re.compile(r"MISSING_(?:TITLE|ARTIST)(?:_|$|\b)", re.IGNORECASE)
VERSIONED_PDF_RE = re.compile(r"^(?P<song_key>.+)__v(?P<version>\d+)\.pdf$")


@dataclass(frozen=True)
class ManifestSong:
    index: int
    source_file: str
    final_file: str
    title: str
    artist: str
    version: int
    song_key: str
    title_slug: str
    artist_slug: str
    book_title: str = ""
    book_song_index: int | None = None


@dataclass(frozen=True)
class UploadItem:
    local_path: Path
    remote_key: str
    content_type: str
    item_type: str
    local_file: str


@dataclass(frozen=True)
class UploadDecision:
    item: UploadItem
    action: str
    reason: str


@dataclass(frozen=True)
class BookMetadata:
    book_title: str
    book_song_index: int


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")

        if key and key not in os.environ:
            os.environ[key] = value


def load_environment() -> None:
    load_dotenv_file(PROJECT_DIR / ".env")
    load_dotenv_file(PROJECT_DIR.parent / ".env")


def get_env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def require_boto3() -> None:
    if boto3 is not None and Config is not None:
        return

    raise SystemExit(
        "boto3 is not installed in this environment. Run `uv sync` from "
        "pdf-processing-engine, then run this script again."
    )


def build_s3_client(endpoint_url: str, region: str):
    require_boto3()

    access_key_id = get_env_value("B2_APPLICATION_KEY_ID", "AWS_ACCESS_KEY_ID")
    secret_access_key = get_env_value(
        "B2_APPLICATION_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "B2_KEY",
    )

    if not access_key_id or not secret_access_key:
        raise SystemExit(
            "Missing B2 credentials. Set B2_APPLICATION_KEY_ID and "
            "B2_APPLICATION_KEY in pdf-processing-engine/.env or your shell."
        )

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def cleaned_prefix(prefix: str) -> str:
    return prefix.strip("/")


def build_remote_key(prefix: str, filename: str) -> str:
    prefix = cleaned_prefix(prefix)
    if not prefix:
        return filename
    return f"{prefix}/{filename}"

def normalized_song_identity(song: ManifestSong) -> tuple[str, str]:
    return song_identity(
        canonicalize_title(song.title),
        canonicalize_artist_text(song.artist),
    )


def versioned_file_name(song_key: str, version: int) -> str:
    return f"{song_key}__v{version:02d}.pdf"


def version_from_file_name(filename: str) -> tuple[str, int] | None:
    match = VERSIONED_PDF_RE.match(filename)
    if match is None:
        return None
    return match.group("song_key"), int(match.group("version"))


def read_manifest(path: Path) -> list[ManifestSong]:
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {
            "index",
            "source_file",
            "final_file",
            "title",
            "artist",
            "version",
            "song_key",
        }
        actual_fields = set(reader.fieldnames or [])
        missing_fields = required_fields - actual_fields
        if missing_fields:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(sorted(missing_fields))}"
            )

        songs = read_manifest_rows(reader)

    if not songs:
        raise ValueError(f"No rows found in manifest: {path}")
    return songs


def read_manifest_rows(reader: csv.DictReader) -> list[ManifestSong]:
    return [
        ManifestSong(
            index=int(row["index"]),
            source_file=row["source_file"],
            final_file=row["final_file"],
            title=row["title"],
            artist=row["artist"],
            book_title=row.get("book_title", ""),
            book_song_index=(
                int(row["book_song_index"])
                if (row.get("book_song_index") or "").strip()
                else None
            ),
            version=int(row["version"]),
            song_key=row["song_key"],
            title_slug=row.get("title_slug", ""),
            artist_slug=row.get("artist_slug", ""),
        )
        for row in reader
    ]


def read_book_metadata(path: Path) -> dict[str, BookMetadata]:
    if not path.exists():
        return {}

    metadata_by_source_file: dict[str, BookMetadata] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {"source_file", "book_title", "book_song_index"}
        missing_fields = required_fields - set(reader.fieldnames or [])
        if missing_fields:
            raise ValueError(
                f"{path} is missing required columns: "
                f"{', '.join(sorted(missing_fields))}"
            )

        for row in reader:
            source_file = (row.get("source_file") or "").strip()
            book_title = (row.get("book_title") or "").strip()
            raw_book_song_index = (row.get("book_song_index") or "").strip()
            if not source_file or not book_title or not raw_book_song_index:
                continue
            metadata_by_source_file[source_file] = BookMetadata(
                book_title=book_title,
                book_song_index=int(raw_book_song_index),
            )

    return metadata_by_source_file


def attach_book_metadata(
    songs: list[ManifestSong],
    metadata_by_source_file: dict[str, BookMetadata],
) -> list[ManifestSong]:
    if not metadata_by_source_file:
        return songs

    enriched_songs: list[ManifestSong] = []
    for song in songs:
        metadata = metadata_by_source_file.get(song.source_file)
        if metadata is None or (song.book_title and song.book_song_index is not None):
            enriched_songs.append(song)
            continue

        enriched_songs.append(
            ManifestSong(
                index=song.index,
                source_file=song.source_file,
                final_file=song.final_file,
                title=song.title,
                artist=song.artist,
                book_title=metadata.book_title,
                book_song_index=metadata.book_song_index,
                version=song.version,
                song_key=song.song_key,
                title_slug=song.title_slug,
                artist_slug=song.artist_slug,
            )
        )

    return enriched_songs


def read_remote_manifest(client, bucket: str, key: str) -> list[ManifestSong]:
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except client.exceptions.ClientError as error:
        status_code = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        error_code = error.response.get("Error", {}).get("Code")
        if status_code == 404 or error_code in {"404", "NoSuchKey", "NotFound"}:
            return []
        raise

    body = response["Body"].read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(body))
    required_fields = {
        "index",
        "source_file",
        "final_file",
        "title",
        "artist",
        "version",
        "song_key",
    }
    missing_fields = required_fields - set(reader.fieldnames or [])
    if missing_fields:
        raise ValueError(
            f"Remote manifest {key} is missing required columns: "
            f"{', '.join(sorted(missing_fields))}"
        )
    return read_manifest_rows(reader)


def reindex_manifest_songs(songs: list[ManifestSong]) -> list[ManifestSong]:
    return [
        ManifestSong(
            index=index,
            source_file=song.source_file,
            final_file=song.final_file,
            title=song.title,
            artist=song.artist,
            book_title=song.book_title,
            book_song_index=song.book_song_index,
            version=song.version,
            song_key=song.song_key,
            title_slug=song.title_slug,
            artist_slug=song.artist_slug,
        )
        for index, song in enumerate(songs)
    ]


def adapt_local_versions(
    remote_songs: list[ManifestSong],
    local_songs: list[ManifestSong],
    remote_keys: set[str] | None = None,
) -> list[ManifestSong]:
    max_remote_versions_by_identity: defaultdict[tuple[str, str], int] = defaultdict(int)
    for song in remote_songs:
        identity = normalized_song_identity(song)
        max_remote_versions_by_identity[identity] = max(
            max_remote_versions_by_identity[identity],
            song.version,
        )

    max_remote_versions_by_song_key: defaultdict[str, int] = defaultdict(int)
    for key in remote_keys or set():
        parsed_version = version_from_file_name(Path(key).name)
        if parsed_version is None:
            continue
        song_key, version = parsed_version
        max_remote_versions_by_song_key[song_key] = max(
            max_remote_versions_by_song_key[song_key],
            version,
        )

    local_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    adapted_songs: list[ManifestSong] = []
    for song in local_songs:
        identity = normalized_song_identity(song)
        local_counts[identity] += 1
        max_remote_version = max(
            max_remote_versions_by_identity[identity],
            max_remote_versions_by_song_key[song.song_key],
        )
        version = max_remote_version + local_counts[identity]
        adapted_songs.append(
            ManifestSong(
                index=song.index,
                source_file=song.source_file,
                final_file=versioned_file_name(song.song_key, version),
                title=song.title,
                artist=song.artist,
                book_title=song.book_title,
                book_song_index=song.book_song_index,
                version=version,
                song_key=song.song_key,
                title_slug=song.title_slug,
                artist_slug=song.artist_slug,
            )
        )
    return adapted_songs


def duplicate_identity_version_files(
    songs: list[ManifestSong],
) -> dict[tuple[str, str, int], set[str]]:
    files_by_identity_version: defaultdict[tuple[str, str, int], set[str]] = (
        defaultdict(set)
    )
    for song in songs:
        identity_version = (*normalized_song_identity(song), song.version)
        files_by_identity_version[identity_version].add(song.final_file)
    return {
        identity_version: files
        for identity_version, files in files_by_identity_version.items()
        if len(files) > 1
    }


def validate_merged_manifest(
    songs: list[ManifestSong],
    allowed_legacy_duplicates: dict[tuple[str, str, int], set[str]] | None = None,
) -> None:
    allowed_legacy_duplicates = allowed_legacy_duplicates or {}
    by_final_file: dict[str, ManifestSong] = {}
    by_identity_version: dict[tuple[str, str, int], ManifestSong] = {}
    for song in songs:
        existing = by_final_file.get(song.final_file)
        if existing is not None:
            raise ValueError(
                f"Merged manifest would contain duplicate final_file={song.final_file!r}"
            )
        by_final_file[song.final_file] = song

        identity_version = (*normalized_song_identity(song), song.version)
        existing = by_identity_version.get(identity_version)
        if existing is not None:
            allowed_files = allowed_legacy_duplicates.get(identity_version, set())
            if {existing.final_file, song.final_file}.issubset(allowed_files):
                continue
            raise ValueError(
                "Merged manifest would contain duplicate catalog version "
                f"title={song.title!r} artist={song.artist!r} version={song.version}. "
                f"Conflicting files: {existing.final_file!r} and {song.final_file!r}"
            )
        by_identity_version[identity_version] = song


def write_manifest(path: Path, songs: list[ManifestSong]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
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
        for song in songs:
            writer.writerow(
                [
                    song.index,
                    song.source_file,
                    song.final_file,
                    song.title,
                    song.artist,
                    song.book_title,
                    song.book_song_index or "",
                    song.version,
                    song.song_key,
                    song.title_slug,
                    song.artist_slug,
                ]
            )


def unresolved_manifest_rows(songs: list[ManifestSong]) -> list[ManifestSong]:
    return [
        song
        for song in songs
        if MISSING_VALUE_RE.search(song.title) or MISSING_VALUE_RE.search(song.artist)
    ]


def build_pdf_upload_items(
    local_songs: list[ManifestSong],
    upload_songs: list[ManifestSong],
    local_dir: Path,
    prefix: str,
) -> list[UploadItem]:
    items: list[UploadItem] = []
    seen_remote_keys: set[str] = set()

    if len(local_songs) != len(upload_songs):
        raise ValueError("Local manifest rows and upload manifest rows must line up")

    for local_song, upload_song in zip(local_songs, upload_songs, strict=True):
        local_path = local_dir / local_song.final_file
        if not local_path.exists():
            raise FileNotFoundError(
                f"Manifest row {local_song.index} references missing PDF: {local_path}"
            )

        remote_key = build_remote_key(prefix, upload_song.final_file)
        if remote_key in seen_remote_keys:
            raise ValueError(f"Duplicate planned remote key: {remote_key}")
        seen_remote_keys.add(remote_key)

        items.append(
            UploadItem(
                local_path=local_path,
                remote_key=remote_key,
                content_type="application/pdf",
                item_type="pdf",
                local_file=local_song.final_file,
            )
        )

    return items


def build_manifest_upload_item(
    manifest_path: Path,
    remote_name: str,
    prefix: str,
) -> UploadItem:
    return UploadItem(
        local_path=manifest_path,
        remote_key=build_remote_key(prefix, remote_name),
        content_type="text/csv",
        item_type="manifest",
        local_file=manifest_path.name,
    )


def remote_key_exists(client, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
    except client.exceptions.ClientError as error:
        status_code = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        error_code = error.response.get("Error", {}).get("Code")
        if status_code == 404 or error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
    return True


def list_remote_keys(client, bucket: str, prefix: str) -> set[str]:
    cleaned = cleaned_prefix(prefix)
    list_prefix = f"{cleaned}/" if cleaned else ""
    paginator = client.get_paginator("list_objects_v2")
    remote_keys: set[str] = set()

    for page in paginator.paginate(Bucket=bucket, Prefix=list_prefix):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if key:
                remote_keys.add(key)

    return remote_keys


def plan_uploads(
    client,
    bucket: str,
    items: list[UploadItem],
    *,
    overwrite: bool,
    existence_check: str,
    prefix: str,
    remote_keys: set[str] | None = None,
) -> list[UploadDecision]:
    decisions: list[UploadDecision] = []
    has_pdf_items = any(item.item_type != "manifest" for item in items)
    listed_remote_keys = None
    if existence_check == "list" and has_pdf_items:
        listed_remote_keys = (
            remote_keys
            if remote_keys is not None
            else list_remote_keys(client, bucket, prefix)
        )

    for item in items:
        if item.item_type == "manifest":
            decisions.append(
                UploadDecision(
                    item=item,
                    action="upload",
                    reason="manifest is always rewritten with the merged catalog",
                )
            )
            continue

        exists = (
            item.remote_key in listed_remote_keys
            if listed_remote_keys is not None
            else remote_key_exists(client, bucket, item.remote_key)
        )
        if exists and not overwrite:
            decisions.append(
                UploadDecision(
                    item=item,
                    action="skip",
                    reason="exact remote key already exists",
                )
            )
        elif exists and overwrite:
            decisions.append(
                UploadDecision(
                    item=item,
                    action="upload",
                    reason="exact remote key exists and --overwrite was supplied",
                )
            )
        else:
            decisions.append(
                UploadDecision(
                    item=item,
                    action="upload",
                    reason="remote key does not exist",
                )
            )

    return decisions


def write_report(path: Path, decisions: list[UploadDecision]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "action",
                "item_type",
                "local_file",
                "planned_remote_key",
                "content_type",
                "reason",
            ]
        )
        for decision in decisions:
            writer.writerow(
                [
                    decision.action,
                    decision.item.item_type,
                    decision.item.local_file,
                    decision.item.remote_key,
                    decision.item.content_type,
                    decision.reason,
                ]
            )


def upload_file(client, bucket: str, decision: UploadDecision) -> None:
    client.upload_file(
        str(decision.item.local_path),
        bucket,
        decision.item.remote_key,
        ExtraArgs={"ContentType": decision.item.content_type},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload versioned PDFs from src/music/final to Backblaze B2 using "
            "manifest.csv as the source of truth."
        )
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=DEFAULT_LOCAL_DIR,
        help="Directory containing final versioned PDFs.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest produced by src/rename_songs.py.",
    )
    parser.add_argument(
        "--book-metadata",
        type=Path,
        default=DEFAULT_BOOK_METADATA,
        help=(
            "Optional source_file-to-book metadata CSV used to enrich local "
            "manifest rows that do not yet contain book_title/book_song_index."
        ),
    )
    parser.add_argument(
        "--bucket",
        default=get_env_value("B2_BUCKET_NAME", "AWS_STORAGE_BUCKET_NAME")
        or DEFAULT_BUCKET,
        help="B2 bucket name.",
    )
    parser.add_argument(
        "--prefix",
        default=get_env_value("B2_PREFIX") or DEFAULT_PREFIX,
        help="Optional remote key prefix/folder inside the bucket.",
    )
    parser.add_argument(
        "--endpoint-url",
        default=get_env_value("AWS_S3_ENDPOINT_URL", "B2_ENDPOINT_URL"),
        help="S3-compatible B2 endpoint URL.",
    )
    parser.add_argument(
        "--region",
        default=get_env_value("AWS_S3_REGION_NAME", "B2_REGION") or DEFAULT_REGION,
        help="B2 S3 region.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="CSV report path for the upload plan.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually upload planned files. Without this flag, this is a dry run.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Upload even when the exact remote key already exists.",
    )
    parser.add_argument(
        "--existence-check",
        choices=["list", "head"],
        default="list",
        help=(
            "How to check for existing remote PDFs. 'list' uses ListObjectsV2 "
            "once per remote prefix page and is the default for large batches. "
            "'head' uses one HeadObject call per local PDF."
        ),
    )
    manifest_mode = parser.add_mutually_exclusive_group()
    manifest_mode.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Only upload PDFs; do not upload manifest.csv.",
    )
    manifest_mode.add_argument(
        "--manifest-only",
        action="store_true",
        help="Only upload the merged manifest.csv and skip all PDFs.",
    )
    parser.add_argument(
        "--merged-manifest",
        type=Path,
        default=None,
        help=(
            "Where to write the merged manifest before upload. Defaults to "
            "reports/b2_merged_manifest.csv."
        ),
    )
    parser.add_argument(
        "--allow-manual-names",
        action="store_true",
        help="Allow execution even if manifest rows contain MISSING_TITLE or MISSING_ARTIST.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console logging level.",
    )
    return parser.parse_args()


def main() -> None:
    load_environment()
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    local_dir = args.local_dir.resolve()
    manifest_path = args.manifest.resolve()
    if not local_dir.exists():
        raise SystemExit(f"Local directory does not exist: {local_dir}")

    songs = read_manifest(manifest_path)
    book_metadata = read_book_metadata(args.book_metadata.resolve())
    songs = attach_book_metadata(songs, book_metadata)
    unresolved_rows = unresolved_manifest_rows(songs)
    if unresolved_rows:
        LOGGER.warning("Manifest contains rows that need manual naming:")
        for song in unresolved_rows:
            LOGGER.warning(
                "  row %s source=%s title=%r artist=%r final=%s",
                song.index + 1,
                song.source_file,
                song.title,
                song.artist,
                song.final_file,
            )
        if args.execute and not args.allow_manual_names:
            raise SystemExit(
                "Refusing to upload unresolved MISSING_* names. Fix corrected_songs.csv "
                "and rerun rename_songs.py, or pass --allow-manual-names to override."
            )

    endpoint_url = args.endpoint_url or f"https://s3.{args.region}.backblazeb2.com"
    client = build_s3_client(endpoint_url=endpoint_url, region=args.region)
    manifest_key = build_remote_key(args.prefix, manifest_path.name)
    remote_songs = read_remote_manifest(client, args.bucket, manifest_key)
    remote_keys = None
    if not args.manifest_only:
        remote_keys = list_remote_keys(client, args.bucket, args.prefix)
    adapted_songs = adapt_local_versions(remote_songs, songs, remote_keys=remote_keys)
    merged_songs = reindex_manifest_songs([*remote_songs, *adapted_songs])
    legacy_duplicates = duplicate_identity_version_files(remote_songs)
    if legacy_duplicates:
        LOGGER.warning(
            "Preserving %s pre-existing normalized catalog-version conflict(s); "
            "new uploads will still be assigned non-conflicting versions.",
            len(legacy_duplicates),
        )
    validate_merged_manifest(
        merged_songs,
        allowed_legacy_duplicates=legacy_duplicates,
    )

    merged_manifest_path = (
        args.merged_manifest.resolve()
        if args.merged_manifest
        else (args.report.resolve().parent / "b2_merged_manifest.csv")
    )
    write_manifest(merged_manifest_path, merged_songs)
    version_adjustments = [
        (local_song, upload_song)
        for local_song, upload_song in zip(songs, adapted_songs, strict=True)
        if local_song.final_file != upload_song.final_file
    ]
    if version_adjustments:
        LOGGER.info(
            "Adjusted %s local PDF names to append after existing remote versions",
            len(version_adjustments),
        )
        for local_song, upload_song in version_adjustments:
            LOGGER.info(
                "  %s -> %s",
                local_song.final_file,
                upload_song.final_file,
            )

    items = []
    if not args.manifest_only:
        items.extend(
            build_pdf_upload_items(
                local_songs=songs,
                upload_songs=adapted_songs,
                local_dir=local_dir,
                prefix=args.prefix,
            )
        )
    if not args.skip_manifest or args.manifest_only:
        items.append(
            build_manifest_upload_item(
                merged_manifest_path,
                manifest_path.name,
                args.prefix,
            )
        )

    planned_pdfs = 0 if args.manifest_only else len(songs)
    manifest_note = (
        " plus merged manifest.csv"
        if not args.skip_manifest or args.manifest_only
        else ""
    )
    if args.manifest_only:
        LOGGER.info(
            "Planning upload of merged manifest only to bucket=%s prefix=%s",
            args.bucket,
            cleaned_prefix(args.prefix) or "(none)",
        )
    else:
        LOGGER.info(
            "Planning upload of %s PDFs%s to bucket=%s prefix=%s",
            planned_pdfs,
            manifest_note,
            args.bucket,
            cleaned_prefix(args.prefix) or "(none)",
        )
    LOGGER.info("Remote manifest rows: %s", len(remote_songs))
    if remote_keys is not None:
        LOGGER.info("Remote keys under prefix: %s", len(remote_keys))
    LOGGER.info("Merged manifest rows: %s", len(merged_songs))

    decisions = plan_uploads(
        client,
        args.bucket,
        items,
        overwrite=args.overwrite,
        existence_check=args.existence_check,
        prefix=args.prefix,
        remote_keys=remote_keys,
    )
    write_report(args.report, decisions)

    upload_decisions = [
        decision for decision in decisions if decision.action == "upload"
    ]
    skip_decisions = [
        decision for decision in decisions if decision.action == "skip"
    ]

    LOGGER.info("Plan written to %s", args.report)
    LOGGER.info(
        "Plan: %s upload, %s skip. Mode: %s",
        len(upload_decisions),
        len(skip_decisions),
        "execute" if args.execute else "dry-run",
    )

    for decision in upload_decisions:
        if args.execute:
            LOGGER.info(
                "Uploading %s -> %s",
                decision.item.local_file,
                decision.item.remote_key,
            )
            upload_file(client, args.bucket, decision)
        else:
            LOGGER.info(
                "Would upload %s -> %s",
                decision.item.local_file,
                decision.item.remote_key,
            )

    if not args.execute:
        LOGGER.info("Dry run complete. Re-run with --execute to upload planned files.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.warning("Cancelled")
        sys.exit(130)
