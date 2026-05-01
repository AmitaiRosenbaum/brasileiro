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

        with patch('songAPI.songs.views.boto3.resource') as mock_b2_resource:
            bucket = MagicMock()
            bucket.objects.all.return_value = [
                MagicMock(key='wave.pdf'),
                MagicMock(key='chega de saudade_joao gilberto e tom jobim.pdf'),
            ]

            mock_b2 = MagicMock()
            mock_b2.meta = MagicMock()
            mock_b2.Bucket.return_value = bucket
            mock_b2_resource.return_value = mock_b2

            response = self.client.get('/songs/getAllSongs')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 2)
        self.assertEqual(response.data['data'][0]['title'], 'wave')
        self.assertEqual(response.data['data'][0]['artists'], [])
        self.assertEqual(response.data['data'][1]['artists'], ['joao gilberto', 'tom jobim'])
        self.assertEqual(Song.objects.count(), 2)
        self.assertTrue(Song.objects.filter(file='wave.pdf').exists())
        self.assertTrue(Artist.objects.filter(name='joao gilberto').exists())

    def test_get_all_songs_creates_distinct_versions_for_duplicate_titles(self):
        self.client.force_authenticate(user=self.user)

        with patch('songAPI.songs.views.boto3.resource') as mock_b2_resource:
            bucket = MagicMock()
            bucket.objects.all.return_value = [
                MagicMock(key='wave.pdf'),
                MagicMock(key='wave_tom jobim.pdf'),
            ]

            mock_b2 = MagicMock()
            mock_b2.meta = MagicMock()
            mock_b2.Bucket.return_value = bucket
            mock_b2_resource.return_value = mock_b2

            response = self.client.get('/songs/getAllSongs')

        self.assertEqual(response.status_code, 200)
        created_songs = Song.objects.filter(name='wave').order_by('version')
        self.assertEqual(created_songs.count(), 2)
        self.assertEqual(list(created_songs.values_list('version', flat=True)), [1, 2])
