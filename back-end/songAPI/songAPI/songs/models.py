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


class Book(models.Model):
    title = models.CharField(max_length=255, unique=True)
    cover_image = models.ImageField(upload_to='book-covers/', blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return self.title


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
    file = models.FileField()

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



extended_song_params = [
    OpenApiParameter('key', type=OpenApiTypes.STR,
                     location=OpenApiParameter.QUERY, required=True, description="Song Key")
]
