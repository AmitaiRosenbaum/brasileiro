import json
from datetime import datetime, timezone

from botocore.exceptions import ClientError


OVERRIDES_FILENAME = 'manual-metadata-overrides.json'


def build_overrides_key(prefix):
    prefix = prefix.strip('/')
    return f'{prefix}/{OVERRIDES_FILENAME}' if prefix else OVERRIDES_FILENAME


def read_overrides(client, bucket, key):
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except ClientError as error:
        error_code = str(error.response.get('Error', {}).get('Code', ''))
        if error_code in {'NoSuchKey', '404', 'NotFound'}:
            return []
        raise

    payload = json.loads(response['Body'].read().decode('utf-8'))
    overrides = payload.get('overrides', [])
    if not isinstance(overrides, list):
        raise ValueError('manual metadata override file must contain an overrides list')
    return overrides


def write_overrides(client, bucket, key, overrides):
    body = json.dumps(
        {'version': 1, 'overrides': overrides},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode('utf-8')
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType='application/json',
    )


def upsert_song_overrides(existing_overrides, songs, title, artist_text, versions):
    by_storage_key = {
        override['storage_key']: dict(override)
        for override in existing_overrides
        if override.get('storage_key')
    }
    updated_at = datetime.now(timezone.utc).isoformat()
    for song in songs:
        storage_key = song.storage_key or song.file.name
        by_storage_key[storage_key] = {
            'storage_key': storage_key,
            'book_title': song.book.title if song.book_id else '',
            'book_song_index': song.book_song_index,
            'title': title,
            'artist': artist_text,
            'version': versions[song.pk],
            'updated_at': updated_at,
        }

    return sorted(
        by_storage_key.values(),
        key=lambda override: (
            override.get('book_title') or '',
            override.get('book_song_index') or 0,
            override['storage_key'],
        ),
    )


def override_for_manifest_row(row, overrides, prefix):
    book_title = (row.get('book_title') or '').strip()
    book_song_index = (row.get('book_song_index') or '').strip()
    storage_key = _storage_key(prefix, row['final_file'].strip())

    if book_title and book_song_index:
        for override in overrides:
            if (
                override.get('book_title') == book_title
                and str(override.get('book_song_index') or '') == book_song_index
            ):
                return override

    for override in overrides:
        if override.get('storage_key') == storage_key:
            return override
    return None


def apply_overrides_to_manifest_rows(rows, overrides, prefix):
    overridden_storage_keys = set()
    updated_rows = []
    for source_row in rows:
        row = dict(source_row)
        override = override_for_manifest_row(row, overrides, prefix)
        if override:
            row['title'] = override['title']
            row['artist'] = override['artist']
            row['version'] = str(override['version'])
            overridden_storage_keys.add(_storage_key(prefix, row['final_file'].strip()))
        updated_rows.append(row)
    return updated_rows, overridden_storage_keys


def _storage_key(prefix, final_file):
    prefix = prefix.strip('/')
    return f'{prefix}/{final_file}' if prefix else final_file
