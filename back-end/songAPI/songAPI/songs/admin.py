from django.contrib import admin
from songAPI.songs.models import Artist, Book, Song


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'cover_image']
    search_fields = ['title']


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'birth', 'death']
    search_fields = ['name']


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['name', 'artist_text', 'version', 'book', 'book_song_index']
    list_filter = ['book']
    search_fields = ['name', 'artist_text', 'book__title']
