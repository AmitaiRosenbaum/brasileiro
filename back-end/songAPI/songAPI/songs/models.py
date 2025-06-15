from django.db import models
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class Song(models.Model):
    KEY_CHOICES = [
        ('C', 'C'), ('C#', 'C♯'), ('Cb', 'C♭'),
        ('D', 'D'), ('D#', 'D♯'), ('Db', 'D♭'),
        ('E', 'E'), ('E#', 'E♯'), ('Eb', 'E♭'),
        ('F', 'F'), ('F#', 'F♯'), ('Fb', 'F♭'),
        ('G', 'G'), ('G#', 'G♯'), ('Gb', 'Gurl♭'),
        ('A', 'A'), ('A#', 'A♯'), ('Ab', 'A♭'),
        ('B', 'B'), ('B#', 'B♯'), ('Bb', 'B♭'),
    ]

    name = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    version = models.IntegerField()
    key = models.CharField(max_length=2, choices=KEY_CHOICES, null=True)
    year = models.IntegerField(null=True)


extended_song_params = [
    OpenApiParameter('key', type=OpenApiTypes.STR,
                     location=OpenApiParameter.QUERY, required=True, description="Song Key")
]
