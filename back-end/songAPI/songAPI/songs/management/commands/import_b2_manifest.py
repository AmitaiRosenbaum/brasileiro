import csv
import json
import re
from collections import defaultdict
from io import StringIO

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F

from songAPI.songs.metadata_overrides import (
    apply_overrides_to_manifest_rows,
    build_overrides_key,
    read_overrides,
)
from songAPI.songs.models import Artist, Book, Song, SongMetadataOverride


def artist_names_from_text(artist_text, split_conjunctions=True):
    pattern = r"\s*,\s*|\s+e\s+" if split_conjunctions else r"\s*,\s*"
    return [
        artist.strip()
        for artist in re.split(pattern, artist_text)
        if artist.strip()
    ]


def build_storage_key(prefix, final_file):
    prefix = prefix.strip("/")
    if not prefix:
        return final_file
    return f"{prefix}/{final_file}"


class Command(BaseCommand):
    help = "Import song metadata from the versioned B2 manifest into Django."

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            help="Local manifest CSV path. If omitted, downloads manifest.csv from B2.",
        )
        parser.add_argument(
            "--prefix",
            default=settings.B2_SONGS_PREFIX,
            help="B2 prefix that contains manifest.csv and PDFs.",
        )
        parser.add_argument(
            "--bucket",
            default=settings.AWS_STORAGE_BUCKET_NAME,
            help="B2 bucket name.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and print counts without writing to the database.",
        )
        parser.add_argument(
            "--overwrite-catalog-metadata",
            action="store_true",
            help=(
                "Overwrite existing song title/artist/version values from the manifest. "
                "By default, existing normalized catalog metadata is preserved and only "
                "storage/book fields are synced."
            ),
        )
        parser.add_argument(
            "--no-repair-version-conflicts",
            action="store_true",
            help=(
                "Do not renumber manifest rows that would collide with existing "
                "or earlier imported song title/artist/version values."
            ),
        )
        parser.add_argument(
            "--metadata-overrides",
            help=(
                "Local manual-metadata-overrides.json path. When importing the B2 "
                "manifest, the persistent B2 override ledger is loaded automatically."
            ),
        )

    def handle(self, *args, **options):
        prefix = options["prefix"].strip("/")
        rows = self._read_rows(options["manifest"], options["bucket"], prefix)
        if not rows:
            raise CommandError("Manifest contains no rows")
        overrides = self._read_manual_overrides(
            options["metadata_overrides"],
            options["manifest"],
            options["bucket"],
            prefix,
        )
        rows, overridden_storage_keys = apply_overrides_to_manifest_rows(
            rows,
            overrides,
            prefix,
        )
        if overridden_storage_keys:
            self.stdout.write(
                f"Applied {len(overridden_storage_keys)} persistent manual metadata overrides."
            )
        if not options["no_repair_version_conflicts"]:
            rows, repairs = self._repair_version_conflicts(
                rows,
                prefix,
                overwrite_catalog_metadata=options["overwrite_catalog_metadata"],
                forced_metadata_keys=overridden_storage_keys,
            )
            if repairs:
                self.stdout.write(
                    self.style.WARNING(
                        f"Repaired {len(repairs)} manifest version conflicts before import."
                    )
                )
                for repair in repairs[:10]:
                    self.stdout.write(
                        "  "
                        f"{repair['final_file']}: v{repair['old_version']} -> "
                        f"v{repair['new_version']} "
                        f"({repair['title']} / {repair['artist']})"
                    )
                if len(repairs) > 10:
                    self.stdout.write(f"  ... and {len(repairs) - 10} more")

        created_count = 0
        updated_count = 0
        with transaction.atomic():
            if overridden_storage_keys:
                Song.objects.filter(storage_key__in=overridden_storage_keys).update(
                    version=F('pk') + 1_000_000,
                )
            for row in rows:
                storage_key = build_storage_key(prefix, row["final_file"].strip())
                created = self._sync_row(
                    row,
                    prefix,
                    dry_run=options["dry_run"],
                    overwrite_catalog_metadata=options["overwrite_catalog_metadata"],
                    force_catalog_metadata=storage_key in overridden_storage_keys,
                )
                if created is True:
                    created_count += 1
                elif created is False:
                    updated_count += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        mode = "Dry run" if options["dry_run"] else "Imported"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} {len(rows)} manifest rows "
                f"({created_count} created, {updated_count} updated)."
            )
        )

    def _read_rows(self, local_manifest, bucket, prefix):
        if local_manifest:
            with open(local_manifest, "r", encoding="utf-8-sig", newline="") as file:
                return list(csv.DictReader(file))

        key = build_storage_key(prefix, "manifest.csv")
        client = boto3.client(
            service_name="s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        try:
            response = client.get_object(Bucket=bucket, Key=key)
        except client.exceptions.ClientError as error:
            raise CommandError(f"Could not download s3://{bucket}/{key}: {error}") from error

        body = response["Body"].read().decode("utf-8-sig")
        return list(csv.DictReader(StringIO(body)))

    def _read_manual_overrides(self, local_path, local_manifest, bucket, prefix):
        if local_path:
            with open(local_path, 'r', encoding='utf-8') as file:
                payload = json.load(file)
            overrides = payload.get('overrides', [])
            if not isinstance(overrides, list):
                raise CommandError('metadata override file must contain an overrides list')
            return overrides

        if local_manifest:
            return []

        client = boto3.client(
            service_name="s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        try:
            return read_overrides(
                client,
                bucket,
                build_overrides_key(prefix),
            )
        except Exception as error:
            raise CommandError(f'Could not load persistent metadata overrides: {error}') from error

    def _repair_version_conflicts(
        self,
        rows,
        prefix,
        overwrite_catalog_metadata,
        forced_metadata_keys=None,
    ):
        rows = [dict(row) for row in rows]
        forced_metadata_keys = forced_metadata_keys or set()
        rows.sort(
            key=lambda row: build_storage_key(prefix, row["final_file"].strip())
            in forced_metadata_keys
        )
        storage_keys = [
            build_storage_key(prefix, row["final_file"].strip())
            for row in rows
            if row.get("final_file")
        ]
        existing_songs_by_storage_key = {
            song.storage_key: song
            for song in Song.objects.filter(storage_key__in=storage_keys)
        }

        used_versions = defaultdict(set)
        for song in Song.objects.exclude(storage_key__in=storage_keys):
            identity = (song.name, song.artist_text)
            used_versions[identity].add(song.version)

        repairs = []
        for row in rows:
            storage_key = build_storage_key(prefix, row["final_file"].strip())
            existing_song = existing_songs_by_storage_key.get(storage_key)
            if (
                existing_song is not None
                and not overwrite_catalog_metadata
                and storage_key not in forced_metadata_keys
            ):
                title = existing_song.name
                artist_text = existing_song.artist_text
                version = existing_song.version
            else:
                title = row["title"].strip()
                artist_text = row["artist"].strip()
                version = int(row["version"])

            identity = (title, artist_text)
            if version in used_versions[identity]:
                old_version = version
                version = max(used_versions[identity], default=0) + 1
                while version in used_versions[identity]:
                    version += 1
                row["version"] = str(version)
                repairs.append(
                    {
                        "final_file": row["final_file"].strip(),
                        "title": title,
                        "artist": artist_text,
                        "old_version": old_version,
                        "new_version": version,
                    }
                )

            used_versions[identity].add(version)

        return rows, repairs

    def _sync_row(
        self,
        row,
        prefix,
        dry_run,
        overwrite_catalog_metadata,
        force_catalog_metadata=False,
    ):
        title = row["title"].strip()
        artist_text = row["artist"].strip()
        version = int(row["version"])
        final_file = row["final_file"].strip()
        storage_key = build_storage_key(prefix, final_file)
        book_title = (row.get("book_title") or "").strip()
        book_song_index = (
            int(row["book_song_index"])
            if (row.get("book_song_index") or "").strip()
            else None
        )
        book = None
        if book_title:
            book, _created = Book.objects.get_or_create(title=book_title)

        song, created = Song.objects.get_or_create(
            storage_key=storage_key,
            defaults={
                "name": title,
                "artist_text": artist_text,
                "version": version,
                "file": storage_key,
                "book": book,
                "book_song_index": book_song_index if book else None,
            },
        )

        changed = created
        if not created:
            sync_fields = {
                "file": storage_key,
                "book": book,
                "book_song_index": book_song_index if book else None,
            }
            if overwrite_catalog_metadata or force_catalog_metadata:
                sync_fields.update(
                    {
                        "name": title,
                        "artist_text": artist_text,
                        "version": version,
                    }
                )

            for field, value in sync_fields.items():
                if getattr(song, field) != value:
                    setattr(song, field, value)
                    changed = True

        if changed and not dry_run:
            song.save()

        if not dry_run and (created or overwrite_catalog_metadata or force_catalog_metadata):
            artists = []
            for artist_name in artist_names_from_text(
                artist_text,
                split_conjunctions=not force_catalog_metadata,
            ):
                artist, _created = Artist.objects.get_or_create(name=artist_name)
                artists.append(artist)
            song.artist.set(artists)

        if not dry_run and force_catalog_metadata:
            SongMetadataOverride.objects.update_or_create(
                storage_key=storage_key,
                defaults={
                    'song': song,
                    'book_title': book_title,
                    'book_song_index': book_song_index,
                    'title': title,
                    'artist_text': artist_text,
                    'version': version,
                },
            )

        return created if changed else None
