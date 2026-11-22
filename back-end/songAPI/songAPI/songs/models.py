import unicodedata

from django.db import models
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class Artist(models.Model):
    name = models.CharField(max_length=100)

    birth = models.DateField(null=True)
    death = models.DateField(null=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name']
    
    def __str__(self) -> str:
        return self.name


def normalize_search_text(value):
    normalized = unicodedata.normalize('NFD', value or '')
    characters = []
    for character in normalized:
        if unicodedata.category(character) == 'Mn':
            continue
        characters.append(character.casefold() if character.isalnum() else ' ')
    return ' '.join(''.join(characters).split())


def build_song_search_text(name, artist_text, book_title=''):
    return normalize_search_text(f'{name} {artist_text} {book_title}')


class Book(models.Model):
    title = models.CharField(max_length=255, unique=True)
    cover_image = models.ImageField(upload_to='book-covers/', blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        previous_title = None
        if self.pk:
            previous_title = (
                type(self).objects
                .filter(pk=self.pk)
                .values_list('title', flat=True)
                .first()
            )
        super().save(*args, **kwargs)

        if previous_title is not None and previous_title != self.title:
            songs = list(self.songs.all())
            for song in songs:
                song.search_text = build_song_search_text(
                    song.name,
                    song.artist_text,
                    self.title,
                )
            Song.objects.bulk_update(songs, ['search_text'])


class Song(models.Model):
    TONIC_CHOICES = map(lambda x: (x, x), ['A', 'B', 'C', 'D', 'E', 'F', 'G'])
    ACCIDENTALS = [('#', '♯'), ('##', '♯♯'), ('b', '♭'), ('bb', '♭♭'), ('', '')]
    MODES = [('major', 'Major'), ('minor', 'Minor'), ('', '')]

    name = models.CharField(max_length=100)
    version = models.IntegerField()
    artist_text = models.CharField(max_length=255, blank=True)
    storage_key = models.CharField(max_length=500, unique=True, null=True, blank=True)

    # Key
    mode = models.CharField(max_length=6, choices=MODES, null=True)
    tonic_base = models.CharField(max_length=1, choices=TONIC_CHOICES, null=True, blank=True)
    tonic_accidental = models.CharField(max_length=2, choices=ACCIDENTALS, null=True, blank=True)

    year = models.IntegerField(null=True)
    genre = models.CharField(max_length=50, null=True)
    file = models.FileField(max_length=500)
    search_text = models.TextField(blank=True, editable=False)

    artist = models.ManyToManyField(Artist)
    book = models.ForeignKey(
        Book,
        null=True,
        blank=True,
        related_name='songs',
        on_delete=models.SET_NULL,
    )
    book_song_index = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'artist_text', 'version']
        constraints = [
            models.UniqueConstraint(
                fields=['book', 'book_song_index'],
                name='unique_song_book_index',
            )
        ]
    
    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        book_title = self.book.title if self.book_id else ''
        self.search_text = build_song_search_text(
            self.name,
            self.artist_text,
            book_title,
        )
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'search_text'}
        super().save(*args, **kwargs)


class SongMetadataOverride(models.Model):
    song = models.ForeignKey(
        Song,
        null=True,
        blank=True,
        related_name='metadata_overrides',
        on_delete=models.SET_NULL,
    )
    storage_key = models.CharField(max_length=500, unique=True)
    book_title = models.CharField(max_length=255, blank=True)
    book_song_index = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=100)
    artist_text = models.CharField(max_length=255)
    version = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['book_title', 'book_song_index', 'storage_key']

    def __str__(self):
        return f'{self.title} — {self.artist_text}'



extended_song_params = [
    OpenApiParameter('key', type=OpenApiTypes.STR,
                     location=OpenApiParameter.QUERY, required=True, description="Song Key")
]
