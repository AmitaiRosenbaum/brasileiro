# PDF Processing Engine

The engine OCRs songbook PDFs, classifies title pages, extracts title/artist
metadata, and uses the title-page boundaries to split each book into song PDFs.

For a detailed explanation of the current classification model, including feature
extraction, title/artist extraction, sequence refinement, known validation cases,
and safe future-change guidance, see
[docs/classification-pipeline.md](docs/classification-pipeline.md).

## Running The Full Five-Book Flow

Run these commands from the repository root:

```bash
cd pdf-processing-engine
.venv/bin/python src/main.py
```

If the local virtual environment does not exist yet, install the dependencies
first:

```bash
cd pdf-processing-engine
poetry install
poetry run python src/main.py
```

By default this does not call any LLM APIs.

To run the full flow and then ask the OpenAI API to correct `songs.csv` into
`corrected_songs.csv`, opt in explicitly:

```bash
cd pdf-processing-engine
.venv/bin/python src/main.py --correct-songs-with-llm
```

You can also run only the correction stage after `songs.csv` already exists:

```bash
cd pdf-processing-engine
.venv/bin/python src/correct_songs_with_llm.py
```

The LLM correction stage reads:

```text
src/music/songs.csv
```

and writes:

```text
src/music/corrected_songs.csv
```

Create `pdf-processing-engine/.env` with:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_MODEL` is optional and defaults to `gpt-4o-mini`. You can also set
`OPENAI_BASE_URL` if you need to use a compatible gateway. The correction script
uses structured JSON output and processes the CSV in chunks so that it can keep
the row count and order stable.

`src/main.py` is currently configured to process all five Bossa Nova books:

```text
SongBook_BossaNova_1: preamble=30, max_pages=137
SongBook_BossaNova_2: preamble=1
SongBook_BossaNova_3: preamble=6
SongBook_BossaNova_4: preamble=5
SongBook_BossaNova_5: preamble=5, max_pages=136
```

The expected source files are:

```text
src/music/SongBook_BossaNova_1.pdf
src/music/SongBook_BossaNova_2.pdf
src/music/SongBook_BossaNova_3.pdf
src/music/SongBook_BossaNova_4.pdf
src/music/SongBook_BossaNova_5.pdf
```

If the corresponding `ocr_*.pdf` files already exist, the engine will reuse them.
If they do not exist, the engine will run `ocrmypdf`, which requires the system
OCR dependencies used by `ocrmypdf`, such as Tesseract and Ghostscript.

By default OCR runs with Tesseract language `por` so Portuguese diacritics are
handled explicitly. You can override this at runtime, for example:

```bash
cd pdf-processing-engine
.venv/bin/python src/main.py --ocr-languages por+eng
```

You can also set:

```bash
OCR_LANGUAGES=por+eng
```

If OCR PDFs already exist and you want to regenerate them with a different
language set, rerun with:

```bash
cd pdf-processing-engine
.venv/bin/python src/main.py --ocr-languages por --redo-ocr
```

Make sure the matching Tesseract language data is installed on the machine, for
example Portuguese support for `por`.

### Before Running

If you changed the source PDFs, OCR PDFs, preambles, or page windows, clear the
cached PDFMiner extraction before running:

```bash
cd pdf-processing-engine
rm -rf pickled/extracted_SongBook_BossaNova_*
```

Classifier and title-extraction code changes do not require clearing this cache,
because the cache stores raw PDFMiner page layouts, not final classifications.

If you want a clean output folder, clear generated outputs first:

```bash
cd pdf-processing-engine
rm -f src/music/songs.csv
rm -rf src/music/split src/music/final
mkdir -p src/music/split src/music/final
```

Do this before rerunning the full flow after a bad or interrupted run. Split
files use one monotonically increasing index across all books, derived from the
highest existing file in `src/music/split`.

Once split files and `songs.csv` have been generated, review/correct the CSV and
save it as:

```text
src/music/corrected_songs.csv
```

Then create the final renamed files:

```bash
cd pdf-processing-engine
.venv/bin/python src/rename_songs.py
```

The renaming step writes versioned, cloud-safe PDF names to:

```text
src/music/final
```

Final files use this format:

```text
title-slug__artist-slug__v01.pdf
```

If the same corrected title and artist occur more than once, later copies are
written as `v02`, `v03`, and so on. The script also writes a metadata manifest:

```text
src/music/final/manifest.csv
```

Review any warnings before upload. Rows containing values such as
`MISSING_TITLE_123` or `MISSING_ARTIST_123` are copied but printed as manual
renaming warnings so they are not uploaded accidentally.

If you want to remove stale PDFs from a previous final run before copying:

```bash
cd pdf-processing-engine
.venv/bin/python src/rename_songs.py --clean
```

## Uploading Final PDFs To B2

The final renamed PDFs are written to:

```text
src/music/final
```

To upload these files to Backblaze B2 without re-uploading files that already
exist under slightly different names, use:

```bash
cd pdf-processing-engine
.venv/bin/python src/scripts/cloud/upload_final_to_b2.py
```

This is a dry run by default. It lists the bucket, compares each local PDF
against the remote PDF filenames, and writes an upload plan to:

```text
reports/b2_upload_plan.csv
```

The comparison is intentionally soft: it ignores case, punctuation, spacing, and
Portuguese diacritics, then uses fuzzy filename similarity. If a remote object
looks similar enough, the local file is skipped. This is designed to avoid
uploading duplicates when the cloud name differs only by a missing space, a
small OCR/name correction, or accents such as `Aguas` vs `Águas`.

Review the plan first. Rows marked `skip` already have a soft match in the
bucket. Rows marked `review` look similar to a remote file, so the script will
not upload them automatically. Rows marked `upload` are the only files uploaded
when execution is enabled.

To perform the upload:

```bash
cd pdf-processing-engine
.venv/bin/python src/scripts/cloud/upload_final_to_b2.py --execute
```

The script defaults to bucket `brasileiro`, matching the backend configuration.
If the real bucket name is different, pass it explicitly:

```bash
cd pdf-processing-engine
.venv/bin/python src/scripts/cloud/upload_final_to_b2.py --bucket your-bucket-name
```

You can also target a folder/prefix:

```bash
cd pdf-processing-engine
.venv/bin/python src/scripts/cloud/upload_final_to_b2.py --prefix songs/final
```

The upload script reads credentials from `pdf-processing-engine/.env` or the
shell. Set:

```bash
B2_APPLICATION_KEY_ID=your_key_id_here
B2_APPLICATION_KEY=your_application_key_here
AWS_S3_REGION_NAME=us-east-005
```

`AWS_S3_REGION_NAME` is optional and defaults to `us-east-005`. You can also set
`AWS_S3_ENDPOINT_URL` if you need a custom S3-compatible B2 endpoint.

The soft-match threshold defaults to `0.88`. Lower values skip more possible
matches; higher values upload more aggressively:

```bash
cd pdf-processing-engine
.venv/bin/python src/scripts/cloud/upload_final_to_b2.py --skip-threshold 0.92
```

There is also a review threshold, defaulting to `0.72`. Matches between the
review and skip thresholds are treated as uncertain and are not uploaded:

```bash
cd pdf-processing-engine
.venv/bin/python src/scripts/cloud/upload_final_to_b2.py --review-threshold 0.80
```

If the environment does not have the B2/S3 SDK yet, refresh dependencies:

```bash
cd pdf-processing-engine
poetry lock
poetry install
```
