from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MUSIC_DIR = SCRIPT_DIR / "music"
CONFIG_PATH = SCRIPT_DIR / "data" / "local_songbooks.json"


def ocr_header(book_name: str, page: int) -> tuple[str, int, str]:
    source = MUSIC_DIR / f"{book_name}.pdf"
    with tempfile.TemporaryDirectory(prefix="brasileiro-header-") as temp_dir:
        image = Path(temp_dir) / "header"
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(page),
                "-l",
                str(page),
                "-r",
                "220",
                "-png",
                "-singlefile",
                "-x",
                "0",
                "-y",
                "0",
                "-W",
                "1819",
                "-H",
                "850",
                str(source),
                str(image),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        result = subprocess.run(
            [
                "tesseract",
                str(image.with_suffix(".png")),
                "stdout",
                "-l",
                "por",
                "--psm",
                "6",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    lines = [" ".join(line.split()) for line in result.stdout.splitlines()]
    useful = [line for line in lines if line]
    return book_name, page, " | ".join(useful[:10])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--books", nargs="*")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    selected = set(args.books or [])
    jobs: list[tuple[str, int]] = []
    for book in config["books"]:
        if book.get("review_status") not in {"ready", "approved"}:
            continue
        if selected and book["name"] not in selected:
            continue
        jobs.extend((book["name"], page) for page in book["manual_start_pages"])

    rows: list[tuple[str, int, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(ocr_header, book_name, page): (book_name, page)
            for book_name, page in jobs
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if completed % 25 == 0 or completed == len(jobs):
                print(f"OCR headers: {completed}/{len(jobs)}", flush=True)

    rows.sort(key=lambda row: (row[0], row[1]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["book_name", "source_page", "header_ocr"])
        writer.writerows(rows)
    print(args.output)


if __name__ == "__main__":
    main()
