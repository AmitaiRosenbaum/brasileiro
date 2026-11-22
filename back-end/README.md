# Back End

## Management Commands

Run these commands from the Django project directory:

```bash
cd /usr/src/app/songAPI
```

For local development from this repository, use:

```bash
cd back-end
uv run python songAPI/manage.py <command>
```

### Importing The B2 Manifest

After the PDF processing engine uploads `manifest.csv` to Backblaze B2, import
it into the Django database:

```bash
python manage.py migrate
python manage.py import_b2_manifest --dry-run
python manage.py import_b2_manifest
```

The dry run downloads the cloud manifest and validates the import inside a
rolled-back transaction. Run the real import only after the dry run completes.

The importer matches existing rows by `storage_key`. By default it preserves
existing normalized catalog metadata for rows that are already in the database,
and only syncs storage and book fields. This matters because production may have
already normalized titles, artists, and versions after an earlier import.

Corrections made through the staff metadata editor are also written to
`manual-metadata-overrides.json` in the B2 song prefix. The cloud importer loads
that ledger automatically and gives it precedence over both the manifest and
existing database metadata. Overrides are matched by book title and song index
first, then by storage key, so they survive regenerated filenames. The same
records are kept in the `SongMetadataOverride` database table and are protected
from later catalogue normalization.

If the manifest would create a duplicate `(name, artist_text, version)` database
row, the importer repairs the incoming row in memory by assigning the next
available version for that exact title/artist pair. You may see output like:

```text
Repaired 1 manifest version conflicts before import.
  some-song__artist__v01.pdf: v1 -> v2 (Some Song / Artist)
```

That repair is intentionally generic. It does not know artist aliases; alias and
title cleanup belongs to `normalize_song_catalog`. The repair only prevents an
actual database uniqueness conflict during manifest import.

To import a local manifest file instead of downloading `manifest.csv` from B2:

```bash
python manage.py import_b2_manifest --manifest /path/to/manifest.csv --dry-run
python manage.py import_b2_manifest --manifest /path/to/manifest.csv
```

For an offline/local import, provide a downloaded override ledger explicitly:

```bash
python manage.py import_b2_manifest \
  --manifest /path/to/manifest.csv \
  --metadata-overrides /path/to/manual-metadata-overrides.json
```

Use `--overwrite-catalog-metadata` only when you deliberately want the manifest
to replace existing normalized title, artist, and version values:

```bash
python manage.py import_b2_manifest --overwrite-catalog-metadata --dry-run
python manage.py import_b2_manifest --overwrite-catalog-metadata
```

### Normalizing The Song Catalog

After importing new manifest rows, run normalization when you want to canonicalize
artist/title aliases and regroup duplicate song versions:

```bash
python manage.py normalize_song_catalog --dry-run
python manage.py normalize_song_catalog
```

Normalization is the place for broad alias handling such as short names,
diacritics, OCR spelling cleanup, and title equivalence. The manifest importer
does not perform that kind of alias resolution.
