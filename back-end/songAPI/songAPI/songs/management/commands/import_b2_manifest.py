import csv
import re
from io import StringIO

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from songAPI.songs.models import Artist, Song


def artist_names_from_text(artist_text):
    return [
        artist.strip()
        for artist in re.split(r"\s*,\s*|\s+e\s+", artist_text)
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

    def handle(self, *args, **options):
        prefix = options["prefix"].strip("/")
        rows = self._read_rows(options["manifest"], options["bucket"], prefix)
        if not rows:
            raise CommandError("Manifest contains no rows")

        created_count = 0
        updated_count = 0
        with transaction.atomic():
            for row in rows:
                created = self._sync_row(row, prefix, dry_run=options["dry_run"])
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

    def _sync_row(self, row, prefix, dry_run):
        title = row["title"].strip()
        artist_text = row["artist"].strip()
        version = int(row["version"])
        final_file = row["final_file"].strip()
        storage_key = build_storage_key(prefix, final_file)

        song, created = Song.objects.get_or_create(
            storage_key=storage_key,
            defaults={
                "name": title,
                "artist_text": artist_text,
                "version": version,
                "file": storage_key,
            },
        )

        changed = created
        if not created:
            for field, value in {
                "name": title,
                "artist_text": artist_text,
                "version": version,
                "file": storage_key,
            }.items():
                if getattr(song, field) != value:
                    setattr(song, field, value)
                    changed = True

        if changed and not dry_run:
            song.save()

        if not dry_run:
            artists = []
            for artist_name in artist_names_from_text(artist_text):
                artist, _created = Artist.objects.get_or_create(name=artist_name)
                artists.append(artist)
            song.artist.set(artists)

        return created if changed else None
