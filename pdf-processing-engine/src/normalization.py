from __future__ import annotations

import re
import unicodedata


ARTIST_SPLIT_RE = re.compile(r"\s*,\s*|\s+e\s+")
MULTISPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def strip_diacritics(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def collapse_whitespace(value: str) -> str:
    return MULTISPACE_RE.sub(" ", value).strip()


def normalized_identity(value: str) -> str:
    normalized = strip_diacritics(collapse_whitespace(value)).casefold()
    normalized = NON_ALNUM_RE.sub(" ", normalized)
    return " ".join(normalized.split())


def canonicalize_title(value: str) -> str:
    return collapse_whitespace(value)


def split_artist_text(artist_text: str) -> list[str]:
    return [
        artist.strip()
        for artist in ARTIST_SPLIT_RE.split(artist_text)
        if artist.strip()
    ]


def canonicalize_artist_names(names: list[str]) -> list[str]:
    canonical_names: list[str] = []
    seen: set[str] = set()

    for name in names:
        canonical_name = collapse_whitespace(name)
        if not canonical_name:
            continue
        identity = normalized_identity(canonical_name)
        if identity in seen:
            continue
        seen.add(identity)
        canonical_names.append(canonical_name)

    return sorted(canonical_names, key=normalized_identity)


def canonicalize_artist_text(artist_text: str) -> str:
    return ", ".join(canonicalize_artist_names(split_artist_text(artist_text)))


def song_identity(title: str, artist_text: str) -> tuple[str, str]:
    canonical_artist_text = canonicalize_artist_text(artist_text)
    return (
        normalized_identity(canonicalize_title(title)),
        normalized_identity(canonical_artist_text),
    )
