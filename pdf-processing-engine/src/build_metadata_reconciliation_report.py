from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "data" / "local_songbooks.json"


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalized(left), normalized(right)).ratio()


def looks_like_credit(line: str) -> bool:
    letters = [character for character in line if character.isalpha()]
    if len(letters) < 4:
        return False
    upper_ratio = sum(character.isupper() for character in letters) / len(letters)
    rejected = ("SONGBOOK", "COPYRIGHT", "TODOS OS DIREITOS")
    return upper_ratio >= 0.82 and not any(value in line.upper() for value in rejected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headers", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pages_by_title = {
        book["title"]: (book["name"], book.get("manual_start_pages", []))
        for book in config["books"]
    }
    with args.headers.open(encoding="utf-8-sig", newline="") as source:
        headers = {
            (row["book_name"], int(row["source_page"])): row["header_ocr"]
            for row in csv.DictReader(source)
        }
    with args.manifest.open(encoding="utf-8-sig", newline="") as source:
        songs = list(csv.DictReader(source))

    output_rows = []
    for song in songs:
        book_name, pages = pages_by_title[song["book_title"]]
        index = int(song["book_song_index"])
        page = pages[index - 1]
        header = headers.get((book_name, page), "")
        lines = [line.strip() for line in header.split("|") if line.strip()]
        ranked_titles = sorted(
            ((similarity(song["title"], line), position, line) for position, line in enumerate(lines)),
            reverse=True,
        )
        title_score, title_position, title_candidate = ranked_titles[0] if ranked_titles else (0, -1, "")
        credit_candidates = [
            (similarity(song["artist"], line), position, line)
            for position, line in enumerate(lines)
            if looks_like_credit(line)
        ]
        after_title = [candidate for candidate in credit_candidates if candidate[1] > title_position]
        ranked_credits = sorted(after_title or credit_candidates, reverse=True)
        artist_score, _, artist_candidate = ranked_credits[0] if ranked_credits else (0, -1, "")
        output_rows.append(
            {
                "book_name": book_name,
                "book_title": song["book_title"],
                "song_index": index,
                "source_page": page,
                "current_title": song["title"],
                "ocr_title": title_candidate,
                "title_score": f"{title_score:.3f}",
                "current_artist": song["artist"],
                "ocr_artist": artist_candidate,
                "artist_score": f"{artist_score:.3f}",
                "header_ocr": header,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Wrote {len(output_rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
