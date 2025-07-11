from pathlib import Path
import os
import re
import requests

ROOT = Path(__file__).resolve().parents[2]
API_URL = 'http://localhost:8000'


def get_song_data():
  all_artists = set()
  all_songs = set()
  
  with open(ROOT / 'data' / 'corrected_songs.csv', 'r') as file:
    next(file)
    for line in file:
      artist_names, song = line.split(';')
      artists = [x.strip() for x in re.split(r'\se\s|,\s', artist_names)]
      all_songs |= {song.strip()}
      all_artists |= set(artists)

  all_artists = all_artists - {'TODO DELETE'}
  all_songs = all_songs - {'TODO DELETE'}
  all_artists = list(all_artists)
  all_songs = list(all_songs)
  all_artists.sort()
  all_songs.sort()
  
  return all_artists, all_songs

def upload_artist():
  artist = {
    "name": "Chico Buarque"
  }
  try:
    response = requests.post(API_URL + "/songs/artist/", json=artist)
    print(response)
  except requests.exceptions.RequestException as e:
    print(e)

def main():
  # artists, songs = get_song_data()
  upload_artist()
  # 1. Upload to S3 bucket
  # 2. Upload artists via Django API
  # 3. Upload songs via Django API
  
  

if __name__ == '__main__':
  main()