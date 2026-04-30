# Brasileiro

Brasileiro is a full-stack sheet music archive for browsing, searching, and opening
PDF scores from a central collection. The repository also includes a standalone
PDF processing pipeline used to turn large songbooks into individual, consistently
named song files for the archive.

![Application architecture](public/app-architecture/architecture.svg)

## Overview

The project is split into three main parts:

- `front-end/`: a React + TypeScript + Vite client for signing in, browsing the
  archive, and opening sheet music in the browser.
- `back-end/`: a Django + Django REST Framework API with session-based
  authentication, song metadata models, and endpoints for retrieving pre-signed
  PDF URLs.
- `pdf-processing-engine/`: a Python pipeline that OCRs songbooks, classifies
  title pages, extracts song metadata, splits books into individual PDFs, and
  prepares files for upload to cloud storage.

## Features

- Session-based login flow for a protected archive.
- Archive home page with search, random suggestions, and collection stats.
- A-Z browsing by song title or artist.
- In-browser PDF viewing via pre-signed cloud URLs.
- REST API with generated schema and Swagger docs.
- PDF ingestion workflow for splitting large books into single-song PDFs.

## Running locally

### Prerequisites

- Docker and Docker Compose
- Backblaze B2 credentials to load PDFs from cloud storage

### 1. Start the app

From the repository root:

```bash
docker compose build
docker compose up
```

This starts:

- frontend at `http://localhost:8080`
- backend at `http://localhost:8000`
- API docs at `http://localhost:8000/docs/`

### 2. Apply database migrations

In a second terminal:

```bash
docker compose exec back-end python manage.py migrate
```

The local SQLite database is persisted in `back-end/data/db.sqlite3`.

### 3. Create a user

To sign into the frontend, create a Django user:

```bash
docker compose exec back-end python manage.py createsuperuser
```

Then open `http://localhost:8080/login` and sign in with that account.

### 4. Configure optional cloud storage access

The backend can generate pre-signed URLs for PDFs stored in Backblaze B2. If you
want the archive pages to return live sheet music, provide these environment
variables to the backend:

```bash
B2_APPLICATION_KEY_ID=your_key_id
B2_APPLICATION_KEY=your_application_key
```

## PDF processing engine

The ingestion pipeline lives in [`pdf-processing-engine/`](pdf-processing-engine/README.md).
It is designed for large sheet music books and currently supports a workflow of:

- adding an OCR layer when needed
- extracting page layout with PDFMiner
- classifying title pages vs continuation pages
- extracting title and artist metadata
- splitting each book into individual song PDFs
- optionally correcting song metadata with an LLM
- renaming and preparing final files for upload

For the detailed classifier and page-splitting design, see
[`pdf-processing-engine/docs/classification-pipeline.md`](pdf-processing-engine/docs/classification-pipeline.md).
