import unicodedata

from django.db import migrations, models


def normalize_search_text(value):
    normalized = unicodedata.normalize('NFD', value or '')
    characters = []
    for character in normalized:
        if unicodedata.category(character) == 'Mn':
            continue
        characters.append(character.casefold() if character.isalnum() else ' ')
    return ' '.join(''.join(characters).split())


def populate_search_text(apps, schema_editor):
    Song = apps.get_model('songs', 'Song')
    songs = list(Song.objects.select_related('book').all())
    for song in songs:
        book_title = song.book.title if song.book_id else ''
        song.search_text = normalize_search_text(
            f'{song.name} {song.artist_text} {book_title}'
        )
    Song.objects.bulk_update(songs, ['search_text'])


def create_postgres_search_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        cursor.execute(
            'CREATE INDEX songs_song_search_text_trgm '
            'ON songs_song USING gin (search_text gin_trgm_ops)'
        )


def drop_postgres_search_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('DROP INDEX IF EXISTS songs_song_search_text_trgm')


class Migration(migrations.Migration):

    dependencies = [
        ('songs', '0009_alter_song_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='search_text',
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.RunPython(populate_search_text, migrations.RunPython.noop),
        migrations.RunPython(create_postgres_search_index, drop_postgres_search_index),
    ]
