from django.db import models

# Create your models here.
class Song(models.Model):
  KEY_CHOICES = [
        ('C', 'C'), ('C#', 'C♯'), ('Cb', 'C♭'),
        ('D', 'D'), ('D#', 'D♯'), ('Db', 'D♭'),
        ('E', 'E'), ('E#', 'E♯'), ('Eb', 'E♭'),
        ('F', 'F'), ('F#', 'F♯'), ('Fb', 'F♭'),
        ('G', 'G'), ('G#', 'G♯'), ('Gb', 'Gurl♭'),
        ('A', 'A'), ('A#', 'A♯'), ('Ab', 'A♭'),
        ('B', 'B'), ('B#', 'B♯'), ('Bb', 'B♭'),
    ]
  url = models.CharField(max_length=200)
  name = models.CharField(max_length=200)
  artist = models.CharField(max_length=200)
  key = models.CharField(max_length=2, choices=KEY_CHOICES)
  year = models.IntegerField()