from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

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
