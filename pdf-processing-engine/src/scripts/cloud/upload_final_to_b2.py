from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import boto3
from botocore.config import Config


SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parents[1]
PROJECT_DIR = SCRIPT_DIR.parents[2]
DEFAULT_LOCAL_DIR = SRC_DIR / "music" / "final"
DEFAULT_BUCKET = "brasileiro"
DEFAULT_REGION = "us-east-005"
DEFAULT_REPORT = PROJECT_DIR / "reports" / "b2_upload_plan.csv"


LOGGER = logging.getLogger("upload_final_to_b2")


@dataclass(frozen=True)
class RemoteObject:
    key: str
    filename: str
    title_name: str
    artist_name: str
    normalized_name: str
    compact_name: str
    token_sorted_name: str


@dataclass(frozen=True)
class UploadDecision:
    local_path: Path
    remote_key: str
    action: str
    matched_remote_key: str
    score: float
    title_score: float
    reason: str


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


def strip_diacritics(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_filename(value: str) -> str:
    stem = Path(value).stem
    stem = strip_diacritics(stem).casefold()
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"[^a-z0-9]+", " ", stem)
    return " ".join(stem.split())


def compact(value: str) -> str:
    return value.replace(" ", "")


def token_sort(value: str) -> str:
    return " ".join(sorted(value.split()))


def split_title_artist(value: str) -> tuple[str, str]:
    stem = Path(value).stem.strip()
    if "_" in stem:
        title, artist = stem.rsplit("_", 1)
        return title.strip(), artist.strip()

    return stem, ""


def sequence_ratio(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def soft_similarity(left: str, right: str) -> float:
    left_normalized = normalize_filename(left)
    right_normalized = normalize_filename(right)

    return max(
        sequence_ratio(left_normalized, right_normalized),
        sequence_ratio(compact(left_normalized), compact(right_normalized)),
        sequence_ratio(token_sort(left_normalized),
                       token_sort(right_normalized)),
    )


def normalized_similarity(left: str, right: str) -> float:
    return max(
        sequence_ratio(left, right),
        sequence_ratio(compact(left), compact(right)),
        sequence_ratio(token_sort(left), token_sort(right)),
    )


def object_from_key(key: str) -> RemoteObject:
    filename = Path(key).name
    title, artist = split_title_artist(filename)
    normalized = normalize_filename(filename)
    return RemoteObject(
        key=key,
        filename=filename,
        title_name=normalize_filename(title),
        artist_name=normalize_filename(artist),
        normalized_name=normalized,
        compact_name=compact(normalized),
        token_sorted_name=token_sort(normalized),
    )


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
        "boto3 is not installed in this environment. Run `poetry install` from "
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


def list_remote_pdfs(client, bucket: str, prefix: str) -> list[RemoteObject]:
    remote_objects: list[RemoteObject] = []
    paginator = client.get_paginator("list_objects_v2")

    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
    for page in page_iterator:
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.lower().endswith(".pdf"):
                remote_objects.append(object_from_key(key))

    return remote_objects


def find_best_remote_match(
    local_path: Path,
    remote_objects: list[RemoteObject],
) -> tuple[RemoteObject | None, float, float]:
    local_title, local_artist = split_title_artist(local_path.name)
    local_title_normalized = normalize_filename(local_title)
    local_artist_normalized = normalize_filename(local_artist)
    local_normalized = normalize_filename(local_path.name)
    local_compact = compact(local_normalized)
    local_token_sorted = token_sort(local_normalized)

    best_object: RemoteObject | None = None
    best_score = 0.0
    best_title_score = 0.0

    for remote_object in remote_objects:
        full_score = max(
            sequence_ratio(local_normalized, remote_object.normalized_name),
            sequence_ratio(local_compact, remote_object.compact_name),
            sequence_ratio(local_token_sorted,
                           remote_object.token_sorted_name),
        )

        title_score = normalized_similarity(
            local_title_normalized,
            remote_object.title_name,
        )

        if local_artist_normalized and remote_object.artist_name:
            artist_score = normalized_similarity(
                local_artist_normalized,
                remote_object.artist_name,
            )
            score = (0.82 * title_score) + (0.18 * artist_score)
        else:
            score = full_score
            title_score = full_score

        if score > best_score:
            best_object = remote_object
            best_score = score
            best_title_score = title_score

    return best_object, best_score, best_title_score


def build_remote_key(prefix: str, local_path: Path) -> str:
    cleaned_prefix = prefix.strip("/")
    if not cleaned_prefix:
        return local_path.name
    return f"{cleaned_prefix}/{local_path.name}"


def plan_uploads(
    local_dir: Path,
    remote_objects: list[RemoteObject],
    prefix: str,
    skip_threshold: float,
    review_threshold: float,
) -> list[UploadDecision]:
    decisions: list[UploadDecision] = []

    for local_path in sorted(local_dir.glob("*.pdf")):
        best_object, best_score, title_score = find_best_remote_match(
            local_path,
            remote_objects,
        )
        remote_key = build_remote_key(prefix, local_path)

        if best_object and best_score >= skip_threshold and title_score >= skip_threshold:
            decisions.append(
                UploadDecision(
                    local_path=local_path,
                    remote_key=remote_key,
                    action="skip",
                    matched_remote_key=best_object.key,
                    score=best_score,
                    title_score=title_score,
                    reason="soft filename match exists in bucket",
                )
            )
        elif best_object and best_score >= review_threshold:
            decisions.append(
                UploadDecision(
                    local_path=local_path,
                    remote_key=remote_key,
                    action="review",
                    matched_remote_key=best_object.key,
                    score=best_score,
                    title_score=title_score,
                    reason="possible remote match; not uploaded automatically",
                )
            )
        else:
            decisions.append(
                UploadDecision(
                    local_path=local_path,
                    remote_key=remote_key,
                    action="upload",
                    matched_remote_key=best_object.key if best_object else "",
                    score=best_score,
                    title_score=title_score,
                    reason="no sufficiently similar remote PDF found",
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
                "score",
                "title_score",
                "local_file",
                "planned_remote_key",
                "matched_remote_key",
                "reason",
            ]
        )
        for decision in decisions:
            writer.writerow(
                [
                    decision.action,
                    f"{decision.score:.4f}",
                    f"{decision.title_score:.4f}",
                    decision.local_path.name,
                    decision.remote_key,
                    decision.matched_remote_key,
                    decision.reason,
                ]
            )


def upload_file(client, bucket: str, decision: UploadDecision) -> None:
    client.upload_file(
        str(decision.local_path),
        bucket,
        decision.remote_key,
        ExtraArgs={"ContentType": "application/pdf"},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload PDFs from src/music/final to a Backblaze B2 bucket, using "
            "soft filename matching to avoid re-uploading near-duplicate names."
        )
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=DEFAULT_LOCAL_DIR,
        help="Directory containing final renamed PDFs.",
    )
    parser.add_argument(
        "--bucket",
        default=get_env_value("B2_BUCKET_NAME", "AWS_STORAGE_BUCKET_NAME")
        or DEFAULT_BUCKET,
        help="B2 bucket name.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional remote key prefix/folder inside the bucket.",
    )
    parser.add_argument(
        "--endpoint-url",
        default=get_env_value("AWS_S3_ENDPOINT_URL", "B2_ENDPOINT_URL"),
        help="S3-compatible B2 endpoint URL.",
    )
    parser.add_argument(
        "--region",
        default=get_env_value("AWS_S3_REGION_NAME",
                              "B2_REGION") or DEFAULT_REGION,
        help="B2 S3 region.",
    )
    parser.add_argument(
        "--skip-threshold",
        type=float,
        default=0.88,
        help=(
            "Similarity score at or above which a local PDF is treated as "
            "already present remotely. Lower values skip more possible matches."
        ),
    )
    parser.add_argument(
        "--review-threshold",
        type=float,
        default=0.72,
        help=(
            "Similarity score at or above which a local PDF is considered "
            "uncertain and left for manual review instead of being uploaded."
        ),
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
    if not local_dir.exists():
        raise SystemExit(f"Local directory does not exist: {local_dir}")

    endpoint_url = args.endpoint_url or f"https://s3.{args.region}.backblazeb2.com"
    client = build_s3_client(endpoint_url=endpoint_url, region=args.region)

    local_count = len(list(local_dir.glob("*.pdf")))
    LOGGER.info("Found %s local PDFs in %s", local_count, local_dir)
    LOGGER.info(
        "Listing remote PDFs from bucket=%s prefix=%s",
        args.bucket,
        args.prefix or "(none)",
    )
    remote_objects = list_remote_pdfs(client, args.bucket, args.prefix)
    LOGGER.info("Found %s remote PDFs to compare against", len(remote_objects))

    decisions = plan_uploads(
        local_dir=local_dir,
        remote_objects=remote_objects,
        prefix=args.prefix,
        skip_threshold=args.skip_threshold,
        review_threshold=args.review_threshold,
    )
    write_report(args.report, decisions)

    upload_decisions = [
        decision for decision in decisions if decision.action == "upload"]
    skip_decisions = [
        decision for decision in decisions if decision.action == "skip"]
    review_decisions = [
        decision for decision in decisions if decision.action == "review"]

    LOGGER.info("Plan written to %s", args.report)
    LOGGER.info(
        "Plan: %s upload, %s skip, %s review. Mode: %s",
        len(upload_decisions),
        len(skip_decisions),
        len(review_decisions),
        "execute" if args.execute else "dry-run",
    )

    for decision in upload_decisions:
        if args.execute:
            LOGGER.info("Uploading %s -> %s",
                        decision.local_path.name, decision.remote_key)
            upload_file(client, args.bucket, decision)
        else:
            LOGGER.info(
                "Would upload %s -> %s (best remote score %.4f: %s)",
                decision.local_path.name,
                decision.remote_key,
                decision.score,
                decision.matched_remote_key or "no remote PDF",
            )

    if not args.execute:
        LOGGER.info(
            "Dry run complete. Re-run with --execute to upload planned files.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.warning("Cancelled")
        sys.exit(130)
