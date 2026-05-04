from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = SCRIPT_DIR / "music" / "songs.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "music" / "corrected_songs.csv"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
ARTIST_SPLIT_RE = re.compile(r"\s*,\s*|\s+e\s+")


def log(message: str) -> None:
    print(f"[correct-songs] {message}", flush=True)


def correct_songs(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    model: str | None = None,
    chunk_size: int = 80,
    max_output_tokens: int = 12000,
) -> None:
    log(f"Loading environment from {PROJECT_DIR / '.env'} and {PROJECT_DIR.parent / '.env'}")
    load_env_files(PROJECT_DIR / ".env", PROJECT_DIR.parent / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to correct songs with the LLM")

    model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    log(f"Reading songs from {input_path}")
    songs = read_songs(input_path)
    log(f"Loaded {len(songs)} songs")
    log(f"Using model={model}, chunk_size={chunk_size}, output={output_path}")
    corrected: list[dict[str, str]] = []

    total_chunks = (len(songs) + chunk_size - 1) // chunk_size
    for chunk_number, chunk_start in enumerate(range(0, len(songs), chunk_size), start=1):
        chunk = songs[chunk_start:chunk_start + chunk_size]
        log(
            f"Submitting chunk {chunk_number}/{total_chunks}: "
            f"rows {chunk[0]['index']}..{chunk[-1]['index']} ({len(chunk)} songs)"
        )
        corrected_chunk = correct_song_chunk(
            chunk,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_output_tokens=max_output_tokens,
        )
        corrected.extend(corrected_chunk)
        log(
            f"Accepted chunk {chunk_number}/{total_chunks}: "
            f"{len(corrected_chunk)} corrected songs, {len(corrected)}/{len(songs)} total"
        )
        if chunk_start + chunk_size < len(songs):
            time.sleep(0.5)

    if len(corrected) != len(songs):
        raise RuntimeError(
            f"Expected {len(songs)} corrected rows, received {len(corrected)}"
        )

    corrected = canonicalize_artist_aliases(
        corrected,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    corrected = canonicalize_song_titles(
        corrected,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    log(f"Writing corrected songs to {output_path}")
    write_songs(output_path, corrected)
    log("Done")


def read_songs(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file, delimiter=";")
        songs: list[dict[str, str]] = []
        for index, row in enumerate(reader):
            artist = (row.get("artist") or "").strip()
            title = (row.get(" title") or row.get("title") or "").strip()
            if artist.lower() == "artist" and title.lower() == "title":
                continue
            songs.append(
                {
                    "index": str(index),
                    "artist": artist,
                    "title": title,
                }
            )
        return songs


def write_songs(path: Path, songs: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=["artist", "title"], delimiter=";")
        writer.writeheader()
        for song in songs:
            writer.writerow(
                {
                    "artist": song["artist"].strip(),
                    "title": song["title"].strip(),
                }
            )


def correct_song_chunk(
    songs: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    max_output_tokens: int,
) -> list[dict[str, str]]:
    chunk_indexes = [song["index"] for song in songs]
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": build_system_prompt(),
            },
            {
                "role": "user",
                "content": json.dumps({"songs": songs}, ensure_ascii=False),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "corrected_songs",
                "strict": True,
                "schema": response_schema(),
            }
        },
        "max_output_tokens": max_output_tokens,
    }
    log(
        f"Calling OpenAI Responses API for {len(songs)} rows "
        f"(indexes {chunk_indexes[0]}..{chunk_indexes[-1]})"
    )
    response = post_json(
        f"{base_url}/responses",
        payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    log("Received API response; extracting structured output")
    response_text = extract_response_text(response)
    log(f"Response text length: {len(response_text)} characters")
    corrected = json.loads(response_text)["songs"]
    log(f"Parsed {len(corrected)} corrected rows from response")
    validate_corrected_chunk(songs, corrected)
    return [
        {
            "artist": row["artist"].strip(),
            "title": row["title"].strip(),
        }
        for row in corrected
    ]


def split_artist_text(artist_text: str) -> list[str]:
    return [
        artist.strip()
        for artist in ARTIST_SPLIT_RE.split(artist_text)
        if artist.strip()
    ]


def normalize_artist_sort_key(value: str) -> str:
    return value.casefold()


def build_artist_alias_map(
    artist_names: list[str],
    *,
    api_key: str,
    base_url: str,
    model: str,
    chunk_size: int = 150,
) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    total_chunks = (len(artist_names) + chunk_size - 1) // chunk_size

    for chunk_number, chunk_start in enumerate(range(0, len(artist_names), chunk_size), start=1):
        chunk = artist_names[chunk_start:chunk_start + chunk_size]
        log(
            f"Canonicalizing artist aliases chunk {chunk_number}/{total_chunks}: "
            f"{len(chunk)} distinct names"
        )
        payload = {
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
        }
        response = post_json(
            f"{base_url}/responses",
            payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        response_text = extract_response_text(response)
        mapped = json.loads(response_text)["artists"]
        validate_artist_mapping(chunk, mapped)
        alias_map.update(
            {
                item["input"].strip(): item["canonical"].strip()
                for item in mapped
            }
        )
        if chunk_start + chunk_size < len(artist_names):
            time.sleep(0.5)

    return alias_map


def apply_artist_alias_map(
    songs: list[dict[str, str]],
    artist_alias_map: dict[str, str],
) -> list[dict[str, str]]:
    normalized_songs: list[dict[str, str]] = []

    for song in songs:
        artist_names = split_artist_text(song["artist"])
        canonical_artists: list[str] = []
        seen: set[str] = set()

        for artist_name in artist_names:
            canonical_name = artist_alias_map.get(
                artist_name, artist_name).strip()
            identity = canonical_name.casefold()
            if not canonical_name or identity in seen:
                continue
            seen.add(identity)
            canonical_artists.append(canonical_name)

        canonical_artists.sort(key=normalize_artist_sort_key)
        normalized_songs.append(
            {
                "artist": ", ".join(canonical_artists),
                "title": song["title"].strip(),
            }
        )

    return normalized_songs


def canonicalize_artist_aliases(
    songs: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
) -> list[dict[str, str]]:
    distinct_artists = sorted(
        {
            artist_name
            for song in songs
            for artist_name in split_artist_text(song["artist"])
        },
        key=normalize_artist_sort_key,
    )
    if not distinct_artists:
        return songs

    artist_alias_map = build_artist_alias_map(
        distinct_artists,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    return apply_artist_alias_map(songs, artist_alias_map)


def build_title_alias_map(
    song_rows: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    chunk_size: int = 150,
) -> dict[tuple[str, str], str]:
    title_map: dict[tuple[str, str], str] = {}
    total_chunks = (len(song_rows) + chunk_size - 1) // chunk_size

    for chunk_number, chunk_start in enumerate(range(0, len(song_rows), chunk_size), start=1):
        chunk = song_rows[chunk_start:chunk_start + chunk_size]
        log(
            f"Canonicalizing title variants chunk {chunk_number}/{total_chunks}: "
            f"{len(chunk)} distinct title+artist pairs"
        )
        payload = {
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": build_title_mapping_prompt(),
                },
                {
                    "role": "user",
                    "content": json.dumps({"songs": chunk}, ensure_ascii=False),
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "title_alias_map",
                    "strict": True,
                    "schema": title_mapping_schema(),
                }
            },
            "max_output_tokens": 16000,
        }
        response = post_json(
            f"{base_url}/responses",
            payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        response_text = extract_response_text(response)
        mapped = json.loads(response_text)["songs"]
        validate_title_mapping(chunk, mapped)
        title_map.update(
            {
                (item["input_title"].strip(), item["input_artist"].strip()): item["canonical_title"].strip()
                for item in mapped
            }
        )
        if chunk_start + chunk_size < len(song_rows):
            time.sleep(0.5)

    return title_map


def apply_title_alias_map(
    songs: list[dict[str, str]],
    title_alias_map: dict[tuple[str, str], str],
) -> list[dict[str, str]]:
    normalized_songs: list[dict[str, str]] = []

    for song in songs:
        title_key = (song["title"].strip(), song["artist"].strip())
        normalized_songs.append(
            {
                "artist": song["artist"].strip(),
                "title": title_alias_map.get(title_key, song["title"]).strip(),
            }
        )

    return normalized_songs


def canonicalize_song_titles(
    songs: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
) -> list[dict[str, str]]:
    distinct_song_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for song in songs:
        key = (song["title"].strip(), song["artist"].strip())
        if key in seen:
            continue
        seen.add(key)
        distinct_song_rows.append(
            {
                "title": key[0],
                "artist": key[1],
            }
        )

    if not distinct_song_rows:
        return songs

    title_alias_map = build_title_alias_map(
        distinct_song_rows,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    return apply_title_alias_map(songs, title_alias_map)


def build_system_prompt() -> str:
    return (
        "You correct OCR-extracted Brazilian song metadata. Return JSON only, "
        "matching the supplied schema. Preserve the number of rows and the exact "
        "input row indexes. Keep the original order. Correct song titles and "
        "artist/composer names for spelling, accents, capitalization, OCR errors, "
        "and Portuguese diacritics such as ã, õ, ç, é, ê, á, à, í, ó, ô, ú. "
        "Prefer canonical Brazilian Portuguese spellings when clear. Remove OCR "
        "junk such as stray chord names, page artifacts, leading numbers, random "
        "letters, and punctuation that is not part of the real name. Keep real "
        "hyphens and apostrophes when they belong to the title. Do not translate "
        "titles. Prefer full canonical composer names instead of nicknames or "
        "short forms when clearly known, for example Tom Jobim should become "
        "Antônio Carlos Jobim. Do not change a row unless the correction is "
        "well supported by the input text or common Bossa Nova / Brazilian "
        "songbook repertoire."
    )


def build_artist_mapping_prompt() -> str:
    return (
        "You canonicalize Brazilian composer and artist names. Return JSON only. "
        "For each input name, output the best canonical display form. Normalize "
        "diacritics, spelling, OCR damage, and common short aliases when they "
        "clearly refer to the same person. Prefer full names with diacritics. "
        "If a name is already canonical or uncertain, keep it unchanged."
    )


def build_title_mapping_prompt() -> str:
    return (
        "You canonicalize Brazilian song titles. Return JSON only. For each input "
        "song row, output the best canonical title for that song. Normalize "
        "capitalization, accents, punctuation, OCR damage, and minor spelling "
        "variants when they clearly refer to the same title. Prefer standard "
        "Brazilian Portuguese title forms with correct diacritics and punctuation. "
        "Keep apostrophes only when they are genuinely part of the title. If the "
        "canonical title is uncertain, keep the input title unchanged."
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


def title_mapping_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "songs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "input_title": {"type": "string"},
                        "input_artist": {"type": "string"},
                        "canonical_title": {"type": "string"},
                    },
                    "required": ["input_title", "input_artist", "canonical_title"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["songs"],
        "additionalProperties": False,
    }


def response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "songs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string"},
                        "artist": {"type": "string"},
                        "title": {"type": "string"},
                    },
                    "required": ["index", "artist", "title"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["songs"],
        "additionalProperties": False,
    }


def validate_corrected_chunk(
    original: list[dict[str, str]],
    corrected: list[dict[str, str]],
) -> None:
    original_indexes = [song["index"] for song in original]
    corrected_indexes = [song.get("index", "<missing>") for song in corrected]
    missing_indexes = [
        index for index in original_indexes if index not in corrected_indexes
    ]
    extra_indexes = [
        index for index in corrected_indexes if index not in original_indexes
    ]

    log(
        "Validating chunk: "
        f"expected={len(original)}, received={len(corrected)}, "
        f"first_expected={original_indexes[0] if original_indexes else 'n/a'}, "
        f"last_expected={original_indexes[-1] if original_indexes else 'n/a'}"
    )
    if missing_indexes:
        log(f"Missing indexes from LLM response: {missing_indexes}")
    if extra_indexes:
        log(f"Unexpected indexes in LLM response: {extra_indexes}")

    if len(corrected) != len(original):
        raise RuntimeError(
            f"Expected {len(original)} corrected rows, received {len(corrected)}. "
            f"Missing indexes: {missing_indexes}. Extra indexes: {extra_indexes}."
        )
    if corrected_indexes != original_indexes:
        raise RuntimeError(
            "LLM response changed row order or indexes: "
            f"expected {original_indexes}, received {corrected_indexes}. "
            f"Missing indexes: {missing_indexes}. Extra indexes: {extra_indexes}."
        )


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


def validate_title_mapping(
    original_rows: list[dict[str, str]],
    mapped_rows: list[dict[str, str]],
) -> None:
    original_set = {
        (row["title"].strip(), row["artist"].strip())
        for row in original_rows
    }
    mapped_set = {
        (row.get("input_title", "").strip(), row.get("input_artist", "").strip())
        for row in mapped_rows
    }
    if original_set != mapped_set:
        missing = sorted(original_set - mapped_set)
        extra = sorted(mapped_set - original_set)
        raise RuntimeError(
            "Title mapping response did not match requested inputs. "
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
            f"OpenAI API request failed: {error.code} {body}") from error


def extract_response_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return response["output_text"]
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise RuntimeError(
        f"Could not find output text in OpenAI response: {response}")


def load_env_files(*paths: Path) -> None:
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=None)
    parser.add_argument("--chunk-size", type=int, default=80)
    parser.add_argument("--max-output-tokens", type=int, default=12000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    correct_songs(
        input_path=args.input,
        output_path=args.output,
        model=args.model,
        chunk_size=args.chunk_size,
        max_output_tokens=args.max_output_tokens,
    )


if __name__ == "__main__":
    main()
