from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from songAPI.authorization.models import Playlist
from songAPI.songs.models import Song


class SessionAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username='testuser',
            password='super-secret-password',
            email='test@example.com',
        )

    def test_csrf_endpoint_sets_token(self):
        response = self.client.get('/auth/csrf/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('csrfToken', response.data)
        self.assertIn('csrftoken', response.cookies)

    def test_login_sets_session_and_me_returns_current_user(self):
        csrf_response = self.client.get('/auth/csrf/')
        csrf_token = csrf_response.data['csrfToken']

        login_response = self.client.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'super-secret-password'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data['user']['username'], 'testuser')
        self.assertIn('sessionid', login_response.cookies)

        me_response = self.client.get('/auth/me/')

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data['user']['email'], 'test@example.com')
        self.assertEqual(len(me_response.data['user']['playlists']), 1)
        self.assertEqual(me_response.data['user']['playlists'][0]['name'], 'Liked Songs')
        self.assertTrue(me_response.data['user']['playlists'][0]['is_liked_songs'])

    def test_logout_clears_authenticated_session(self):
        csrf_response = self.client.get('/auth/csrf/')
        csrf_token = csrf_response.data['csrfToken']

        login_response = self.client.post(
            '/auth/login/',
            {'username': 'testuser', 'password': 'super-secret-password'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        rotated_csrf_token = login_response.data['csrfToken']

        logout_response = self.client.post(
            '/auth/logout/',
            {},
            format='json',
            HTTP_X_CSRFTOKEN=rotated_csrf_token,
        )

        self.assertEqual(logout_response.status_code, 204)

        me_response = self.client.get('/auth/me/')

        self.assertEqual(me_response.status_code, 403)

    def test_user_gets_default_liked_songs_playlist_on_create(self):
        liked_songs = Playlist.objects.filter(user=self.user, is_liked_songs=True)

        self.assertEqual(liked_songs.count(), 1)
        self.assertEqual(liked_songs.first().name, 'Liked Songs')

    def test_authenticated_user_can_update_own_settings(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            '/auth/me/',
            {
                'email': 'updated@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'username': 'ignored-change',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')


class PlaylistApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='playlist-owner',
            password='super-secret-password',
            email='owner@example.com',
        )
        self.other_user = User.objects.create_user(
            username='other-user',
            password='super-secret-password',
        )
        self.song = Song.objects.create(
            name='Asa Branca',
            version=1,
            file='asa-branca.pdf',
        )

    def test_playlist_list_is_scoped_to_authenticated_user(self):
        Playlist.objects.create(user=self.other_user, name='Private Mix')
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/playlists/')

        self.assertEqual(response.status_code, 200)
        returned_names = [playlist['name'] for playlist in response.data['results']]
        self.assertEqual(returned_names, ['Liked Songs'])

    def test_authenticated_user_can_create_custom_playlist(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/playlists/',
            {'name': 'Road Trip', 'songs': [self.song.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Road Trip')
        self.assertFalse(response.data['is_liked_songs'])
        self.assertEqual(response.data['songs'], [self.song.id])
        self.assertTrue(
            Playlist.objects.filter(user=self.user, name='Road Trip', songs=self.song).exists()
        )
        playlist = Playlist.objects.get(user=self.user, name='Road Trip')
        self.assertEqual(playlist.song_order, [self.song.id])

    def test_authenticated_user_cannot_access_another_users_playlist(self):
        playlist = Playlist.objects.create(user=self.other_user, name='Other Playlist')
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/playlists/{playlist.id}/')

        self.assertEqual(response.status_code, 404)

    def test_authenticated_user_can_delete_custom_playlist(self):
        playlist = Playlist.objects.create(user=self.user, name='Road Trip')
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/playlists/{playlist.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Playlist.objects.filter(id=playlist.id).exists())

    def test_authenticated_user_cannot_delete_liked_songs_playlist(self):
        playlist = Playlist.objects.get(user=self.user, is_liked_songs=True)
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f'/playlists/{playlist.id}/')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Playlist.objects.filter(id=playlist.id).exists())

    def test_authenticated_user_can_reorder_playlist_songs(self):
        second_song = Song.objects.create(
            name='Wave',
            version=1,
            file='wave.pdf',
        )
        playlist = Playlist.objects.create(user=self.user, name='Road Trip')
        playlist.songs.set([self.song, second_song])
        playlist.song_order = [self.song.id, second_song.id]
        playlist.save(update_fields=['song_order'])
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f'/playlists/{playlist.id}/',
            {'songs': [second_song.id, self.song.id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        playlist.refresh_from_db()
        self.assertEqual(response.data['songs'], [second_song.id, self.song.id])
        self.assertEqual(playlist.song_order, [second_song.id, self.song.id])
