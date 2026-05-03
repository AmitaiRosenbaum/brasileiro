from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from songAPI.songs.models import Artist, Song


ARTIST_SPLIT_RE = re.compile(r"\s*,\s*|\s+e\s+")
MULTISPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def strip_diacritics(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def collapse_whitespace(value: str) -> str:
    return MULTISPACE_RE.sub(" ", value).strip()


def normalized_identity(value: str) -> str:
    normalized = strip_diacritics(collapse_whitespace(value)).casefold()
    normalized = NON_ALNUM_RE.sub(" ", normalized)
    return " ".join(normalized.split())


def split_artist_text(artist_text: str) -> list[str]:
    return [
        artist.strip()
        for artist in ARTIST_SPLIT_RE.split(artist_text)
        if artist.strip()
    ]


def normalize_artist_names(
    names: list[str],
    artist_alias_map: dict[str, str],
) -> list[str]:
    normalized_names: list[str] = []
    seen: set[str] = set()

    for name in names:
        cleaned_name = collapse_whitespace(name)
        if not cleaned_name:
            continue
        canonical_name = artist_alias_map.get(cleaned_name, cleaned_name)
        identity = normalized_identity(canonical_name)
        if identity in seen:
            continue
        seen.add(identity)
        normalized_names.append(canonical_name)

    return sorted(normalized_names, key=normalized_identity)


def build_song_identity(title: str, artist_text: str) -> tuple[str, str]:
    return (
        normalized_identity(collapse_whitespace(title)),
        normalized_identity(artist_text),
    )


def build_artist_alias_map_with_llm(
    artist_names: list[str],
    *,
    api_key: str,
    model: str,
    base_url: str,
    chunk_size: int,
) -> dict[str, str]:
    alias_map: dict[str, str] = {}

    for start in range(0, len(artist_names), chunk_size):
        chunk = artist_names[start:start + chunk_size]
        response = post_json(
            f"{base_url}/responses",
            {
                "model": model,
                "input": [
                    {
                        "role": "system",
                        "content": build_artist_mapping_prompt(),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"artists": chunk}, ensure_ascii=False),
                    },
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "artist_alias_map",
                        "strict": True,
                        "schema": artist_mapping_schema(),
                    }
                },
                "max_output_tokens": 16000,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        response_text = extract_response_text(response)
        payload = json.loads(response_text)
        validate_artist_mapping(chunk, payload["artists"])
        alias_map.update(
            {
                item["input"].strip(): collapse_whitespace(item["canonical"])
                for item in payload["artists"]
            }
        )
        if start + chunk_size < len(artist_names):
            time.sleep(0.5)

    return alias_map


def build_artist_mapping_prompt() -> str:
    return (
        "You canonicalize Brazilian composer and artist names. Return JSON only. "
        "For each input name, output the best canonical display form. Normalize "
        "diacritics, spelling, OCR damage, and common short aliases when they "
        "clearly refer to the same person. Prefer full names with diacritics, "
        "for example nicknames like Tom Jobim should map to Antônio Carlos Jobim "
        "when clear. If a name is already canonical or the match is uncertain, "
        "keep it unchanged."
    )


def artist_mapping_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "artists": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "canonical": {"type": "string"},
                    },
                    "required": ["input", "canonical"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["artists"],
        "additionalProperties": False,
    }


def validate_artist_mapping(
    original_names: list[str],
    mapped_names: list[dict[str, str]],
) -> None:
    original_set = {name.strip() for name in original_names}
    mapped_set = {item.get("input", "").strip() for item in mapped_names}
    if original_set != mapped_set:
        missing = sorted(original_set - mapped_set)
        extra = sorted(mapped_set - original_set)
        raise RuntimeError(
            "Artist alias mapping response did not match requested inputs. "
            f"Missing={missing}, extra={extra}."
        )


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8")
        raise RuntimeError(
            f"OpenAI API request failed: {error.code} {body}"
        ) from error


def extract_response_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return response["output_text"]
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise RuntimeError(f"Could not find output text in OpenAI response: {response}")


class Command(BaseCommand):
    help = (
        "One-off cleanup for the Django song catalog. Canonicalizes artist text, "
        "rebuilds M2M artists, and regroups duplicate song versions."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--with-llm",
            action="store_true",
            help="Use the OpenAI API to resolve aliases like nicknames and short forms.",
        )
        parser.add_argument(
            "--artist-alias-json",
            type=Path,
            default=None,
            help="Optional JSON object mapping current artist names to canonical names.",
        )
        parser.add_argument("--model", default=None)
        parser.add_argument("--artist-chunk-size", type=int, default=150)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        with_llm = options["with_llm"]
        alias_map = self._load_alias_map(options["artist_alias_json"])
        model = options["model"] or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

        songs = list(Song.objects.prefetch_related("artist").order_by("name", "version", "id"))
        if not songs:
            self.stdout.write(self.style.WARNING("No songs found."))
            return

        if with_llm:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise CommandError("OPENAI_API_KEY is required with --with-llm.")
            artist_names = sorted(
                {
                    collapse_whitespace(name)
                    for song in songs
                    for name in (
                        [artist.name for artist in song.artist.all()]
                        or split_artist_text(song.artist_text)
                    )
                    if collapse_whitespace(name)
                },
                key=normalized_identity,
            )
            alias_map.update(
                build_artist_alias_map_with_llm(
                    artist_names,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    chunk_size=options["artist_chunk_size"],
                )
            )

        canonical_song_data: dict[int, dict[str, Any]] = {}
        groups: defaultdict[tuple[str, str], list[Song]] = defaultdict(list)

        for song in songs:
            artist_names = [artist.name for artist in song.artist.all()]
            if not artist_names:
                artist_names = split_artist_text(song.artist_text)
            normalized_artists = normalize_artist_names(artist_names, alias_map)
            canonical_artist_text = ", ".join(normalized_artists)
            canonical_title = collapse_whitespace(song.name)
            canonical_song_data[song.pk] = {
                "title": canonical_title,
                "artist_names": normalized_artists,
                "artist_text": canonical_artist_text,
            }
            groups[build_song_identity(canonical_title, canonical_artist_text)].append(song)

        version_reassignments = 0
        artist_text_updates = 0
        title_updates = 0
        artist_name_updates = 0

        for group in groups.values():
            ordered_group = sorted(group, key=lambda song: (song.version, song.id))
            for version, song in enumerate(ordered_group, start=1):
                data = canonical_song_data[song.pk]
                data["version"] = version
                if song.version != version:
                    version_reassignments += 1
                if song.artist_text != data["artist_text"]:
                    artist_text_updates += 1
                if song.name != data["title"]:
                    title_updates += 1
                if [artist.name for artist in song.artist.all()] != data["artist_names"]:
                    artist_name_updates += 1

        with transaction.atomic():
            for song in songs:
                data = canonical_song_data[song.pk]
                temp_version = 1_000_000 + song.pk
                changed_fields = []
                if song.version != temp_version:
                    song.version = temp_version
                    changed_fields.append("version")
                if song.artist_text != data["artist_text"]:
                    song.artist_text = data["artist_text"]
                    changed_fields.append("artist_text")
                if song.name != data["title"]:
                    song.name = data["title"]
                    changed_fields.append("name")
                if changed_fields and not dry_run:
                    song.save(update_fields=changed_fields)

            for song in songs:
                data = canonical_song_data[song.pk]
                final_fields = []
                if song.version != data["version"]:
                    song.version = data["version"]
                    final_fields.append("version")
                if song.artist_text != data["artist_text"]:
                    song.artist_text = data["artist_text"]
                    final_fields.append("artist_text")
                if song.name != data["title"]:
                    song.name = data["title"]
                    final_fields.append("name")

                canonical_artists = []
                for artist_name in data["artist_names"]:
                    artist, _created = Artist.objects.get_or_create(name=artist_name)
                    canonical_artists.append(artist)

                if not dry_run:
                    if final_fields:
                        song.save(update_fields=final_fields)
                    song.artist.set(canonical_artists)

            if not dry_run:
                Artist.objects.filter(song__isnull=True).delete()
            else:
                transaction.set_rollback(True)

        mode = "Dry run" if dry_run else "Normalized"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} {len(songs)} songs across {len(groups)} canonical groups. "
                f"Updated titles={title_updates}, artist_text={artist_text_updates}, "
                f"artist_lists={artist_name_updates}, reassigned_versions={version_reassignments}."
            )
        )

    def _load_alias_map(self, path: Path | str | None) -> dict[str, str]:
        if path is None:
            return {}
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise CommandError("--artist-alias-json must contain a JSON object.")
        return {
            collapse_whitespace(str(key)): collapse_whitespace(str(value))
            for key, value in payload.items()
            if collapse_whitespace(str(key)) and collapse_whitespace(str(value))
        }
