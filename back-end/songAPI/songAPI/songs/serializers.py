from rest_framework import serializers
from songAPI.songs.models import Song, Artist


class SongSerializer(serializers.ModelSerializer):
  class Meta:
    model = Song
    fields = ['name', 'version', 'artist_text', 'storage_key', 'mode', 'tonic_base', 'tonic_accidental', 'year', 'genre', 'file', 'artist']


class ArtistSerializer(serializers.ModelSerializer):
  class Meta:
    model = Artist
    fields = ['id', 'name', 'birth', 'death']
