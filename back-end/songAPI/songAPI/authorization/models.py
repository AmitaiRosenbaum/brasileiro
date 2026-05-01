from django.db import models
from django.contrib.auth.models import User
from songAPI.songs.models import Artist, Song


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    artists = models.ManyToManyField(Artist)
    songs = models.ManyToManyField(Song)

    def __str__(self) -> str:
        return f"{self.user.get_username()}'s Profile"


class Playlist(models.Model):
    DEFAULT_LIKED_SONGS_NAME = 'Liked Songs'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=100)
    songs = models.ManyToManyField(Song, blank=True, related_name='playlists')
    is_liked_songs = models.BooleanField(default=False)

    class Meta:
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_playlist_name_per_user'),
            models.UniqueConstraint(
                fields=['user', 'is_liked_songs'],
                condition=models.Q(is_liked_songs=True),
                name='unique_liked_songs_playlist_per_user',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.is_liked_songs and not self.name:
            self.name = self.DEFAULT_LIKED_SONGS_NAME
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.get_username()} - {self.name}"
