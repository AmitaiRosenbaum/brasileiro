from rest_framework import serializers
from songAPI.songs.models import Song


class SongSerializer(serializers.ModelSerializer):
  class Meta:
    model = Song
    fields = ['name', 'artist', 'version', 'key', 'year']