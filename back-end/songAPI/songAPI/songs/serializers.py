from rest_framework import serializers
from songAPI.songs.models import Book, Song, Artist


class BookSerializer(serializers.ModelSerializer):
  class Meta:
    model = Book
    fields = ['id', 'title', 'cover_image']


class SongSerializer(serializers.ModelSerializer):
  class Meta:
    model = Song
    fields = ['name', 'version', 'artist_text', 'storage_key', 'mode', 'tonic_base', 'tonic_accidental', 'year', 'genre', 'file', 'artist', 'book', 'book_song_index']


class ArtistSerializer(serializers.ModelSerializer):
  class Meta:
    model = Artist
    fields = ['id', 'name', 'birth', 'death']
