from rest_framework import serializers
from songAPI.songs.models import Song


class SongSerializer(serializers.HyperlinkedModelSerializer):
  class Meta:
    model = Song
    fields = '__all__'