from django.contrib import admin
from songAPI.songs.models import Artist, Book, Song, SongMetadataOverride


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


@admin.register(SongMetadataOverride)
class SongMetadataOverrideAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'artist_text',
        'book_title',
        'book_song_index',
        'updated_at',
    ]
    search_fields = ['title', 'artist_text', 'book_title', 'storage_key']
    readonly_fields = [
        'song',
        'storage_key',
        'book_title',
        'book_song_index',
        'title',
        'artist_text',
        'version',
        'updated_at',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
