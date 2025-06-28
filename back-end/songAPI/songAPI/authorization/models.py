from django.db import models
from django.contrib.auth.models import User
from songAPI.songs.models import Artist, Song

# Create your models here.
class Profile(models.Model):
  user = models.OneToOneField(User, on_delete=models.CASCADE)
  artists = models.ManyToManyField(Artist)
  songs = models.ManyToManyField(Song)


  def __str__(self) -> str:
    return f'{self.user.get_username()}\'s Profile'