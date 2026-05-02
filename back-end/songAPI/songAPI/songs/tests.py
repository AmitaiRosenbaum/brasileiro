from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch

from songAPI.songs.models import Artist, Song


class SongsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='song-tester',
            password='super-secret-password',
        )

    def test_song_list_requires_authentication(self):
        response = self.client.get('/songs/')

        self.assertEqual(response.status_code, 403)

    def test_song_url_requires_authentication(self):
        response = self.client.get('/songs/getSongUrl', {'key': 'example.pdf'})

        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_list_songs(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/songs/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

    def test_authenticated_user_can_get_all_song_metadata_with_ids(self):
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='tom jobim')
        song = Song.objects.create(
            name='wave',
            version=1,
            artist_text='tom jobim',
            file='brasileiro-songs/wave__tom-jobim__v01.pdf',
            storage_key='brasileiro-songs/wave__tom-jobim__v01.pdf',
        )
        song.artist.add(artist)

        with patch('songAPI.songs.views.boto3.resource') as mock_b2_resource:
            response = self.client.get('/songs/getAllSongs')

        mock_b2_resource.assert_not_called()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['title'], 'wave')
        self.assertEqual(response.data['data'][0]['artists'], ['tom jobim'])
        self.assertEqual(response.data['data'][0]['versions'][0]['version'], 1)
        self.assertEqual(Song.objects.count(), 1)

    def test_get_all_songs_groups_distinct_versions_for_duplicate_titles(self):
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='tom jobim')
        for version in [1, 2]:
            song = Song.objects.create(
                name='wave',
                version=version,
                artist_text='tom jobim',
                file=f'brasileiro-songs/wave__tom-jobim__v{version:02d}.pdf',
                storage_key=f'brasileiro-songs/wave__tom-jobim__v{version:02d}.pdf',
            )
            song.artist.add(artist)

        response = self.client.get('/songs/getAllSongs')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['title'], 'wave')
        self.assertEqual(
            [version['version'] for version in response.data['data'][0]['versions']],
            [1, 2],
        )

    def test_get_all_songs_keeps_same_title_different_artist_separate(self):
        self.client.force_authenticate(user=self.user)
        for artist_name in ['tom jobim', 'chico buarque']:
            artist = Artist.objects.create(name=artist_name)
            song = Song.objects.create(
                name='sabiá',
                version=1,
                artist_text=artist_name,
                file=f'brasileiro-songs/sabia__{artist_name.replace(" ", "-")}__v01.pdf',
                storage_key=f'brasileiro-songs/sabia__{artist_name.replace(" ", "-")}__v01.pdf',
            )
            song.artist.add(artist)

        response = self.client.get('/songs/getAllSongs')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 2)
