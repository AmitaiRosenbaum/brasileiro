from django.db import models
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class Artist(models.Model):
    name = models.CharField(max_length=100)

    birth = models.DateField(null=True)
    death = models.DateField(null=True)


class Song(models.Model):
    TONIC_CHOICES = map(lambda x: (x, x), ['A', 'B', 'C', 'D', 'E', 'F', 'G'])
    ACCIDENTALS = [('#', '♯'), ('##', '♯♯'), ('b', '♭'), ('bb', '♭♭'), ('', '')]
    MODES = [('major', 'Major'), ('minor', 'Minor'), ('', '')]

    name = models.CharField(max_length=100)
    version = models.IntegerField()

    # Key
    mode = models.CharField(max_length=6, choices=MODES, null=True)
    tonic_base = models.CharField(max_length=1, choices=TONIC_CHOICES, null=True, blank=True)
    tonic_accidental = models.CharField(max_length=2, choices=ACCIDENTALS, null=True, blank=True)

    year = models.DateField(null=True)
    genre = models.CharField(max_length=50, null=True)
    filename = models.CharField(max_length=200)

    artist = models.ManyToManyField(Artist)



extended_song_params = [
    OpenApiParameter('key', type=OpenApiTypes.STR,
                     location=OpenApiParameter.QUERY, required=True, description="Song Key")
]
