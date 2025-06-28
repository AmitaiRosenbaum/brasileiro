from rest_framework import serializers
from songAPI.songs.models import Song, Artist


class SongSerializer(serializers.ModelSerializer):
  class Meta:
    model = Song
    fields = ['name', 'version', 'mode', 'tonic_base', 'tonic_accidental', 'year', 'genre', 'filename', 'artist']


class ArtistSerializer(serializers.ModelSerializer):
  class Meta:
    model = Artist
    fields = ['name', 'birth', 'death']