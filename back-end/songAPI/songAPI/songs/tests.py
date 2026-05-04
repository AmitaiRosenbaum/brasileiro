from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import json

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

    def test_get_all_songs_groups_same_artists_with_reordered_text(self):
        self.client.force_authenticate(user=self.user)
        variant_rows = [
            ('Olha Maria', 'Antonio Carlos Jobim, Chico Buarque, Vinicius de Moraes'),
            ('Olha Maria', 'Chico Buarque, Vinicius de Moraes, Antonio Carlos Jobim'),
        ]

        for index, (_title, artist_text) in enumerate(variant_rows, start=1):
            song = Song.objects.create(
                name='Olha Maria',
                version=1,
                artist_text=artist_text,
                file=f'brasileiro-songs/olha-maria-{index}.pdf',
                storage_key=f'brasileiro-songs/olha-maria-{index}.pdf',
            )
            for artist_name in [name.strip() for name in artist_text.split(',')]:
                artist, _created = Artist.objects.get_or_create(name=artist_name)
                song.artist.add(artist)

        response = self.client.get('/songs/getAllSongs')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 2)

    def test_get_all_songs_can_paginate_title_results(self):
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='tom jobim')
        for index in range(3):
            song = Song.objects.create(
                name=f'song {index}',
                version=1,
                artist_text='tom jobim',
                file=f'brasileiro-songs/song-{index}.pdf',
                storage_key=f'brasileiro-songs/song-{index}.pdf',
            )
            song.artist.add(artist)

        response = self.client.get('/songs/getAllSongs', {'mode': 'title', 'page': 2, 'page_size': 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['pagination']['page'], 2)
        self.assertEqual(response.data['pagination']['total'], 3)
        self.assertEqual(response.data['pagination']['total_pages'], 2)

    def test_get_all_songs_can_paginate_within_title_section(self):
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='tom jobim')
        for title in ['A Felicidade', 'Triste', 'Wave']:
            song = Song.objects.create(
                name=title,
                version=1,
                artist_text='tom jobim',
                file=f'brasileiro-songs/{title}.pdf',
                storage_key=f'brasileiro-songs/{title}.pdf',
            )
            song.artist.add(artist)

        response = self.client.get(
            '/songs/getAllSongs',
            {'mode': 'title', 'section': 'T', 'page': 1, 'page_size': 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pagination']['total'], 1)
        self.assertEqual(response.data['pagination']['sections'], ['A', 'T', 'W'])
        self.assertEqual(response.data['data'][0]['title'], 'Triste')

    def test_get_all_songs_can_paginate_artist_results(self):
        self.client.force_authenticate(user=self.user)
        antonio = Artist.objects.create(name='Antonio Carlos Jobim')
        chico = Artist.objects.create(name='Chico Buarque')
        song = Song.objects.create(
            name='Olha Maria',
            version=1,
            artist_text='Antonio Carlos Jobim, Chico Buarque',
            file='brasileiro-songs/olha-maria.pdf',
            storage_key='brasileiro-songs/olha-maria.pdf',
        )
        song.artist.add(antonio, chico)

        response = self.client.get('/songs/getAllSongs', {'mode': 'artist', 'page_size': 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['pagination']['total'], 2)
        self.assertEqual(response.data['data'][0]['artists'], ['Antonio Carlos Jobim'])

    def test_get_all_songs_search_limits_typeahead_results(self):
        self.client.force_authenticate(user=self.user)
        jobim = Artist.objects.create(name='Tom Jobim')
        caetano = Artist.objects.create(name='Caetano Veloso')
        wave = Song.objects.create(
            name='Wave',
            version=1,
            artist_text='Tom Jobim',
            file='brasileiro-songs/wave.pdf',
            storage_key='brasileiro-songs/wave.pdf',
        )
        alegria = Song.objects.create(
            name='Alegria Alegria',
            version=1,
            artist_text='Caetano Veloso',
            file='brasileiro-songs/alegria.pdf',
            storage_key='brasileiro-songs/alegria.pdf',
        )
        wave.artist.add(jobim)
        alegria.artist.add(caetano)

        response = self.client.get('/songs/getAllSongs', {'search': 'jobim', 'page_size': 5})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pagination']['total'], 1)
        self.assertEqual(response.data['data'][0]['title'], 'Wave')

    def test_get_all_songs_can_fetch_single_song_group_by_legacy_key(self):
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='Tom Jobim')
        song = Song.objects.create(
            name='Wave',
            version=1,
            artist_text='Tom Jobim',
            file='brasileiro-songs/wave.pdf',
            storage_key='brasileiro-songs/wave.pdf',
        )
        song.artist.add(artist)

        response = self.client.get('/songs/getAllSongs', {'key': 'brasileiro-songs/wave.pdf'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['id'], song.id)

    def test_normalize_song_catalog_merges_alias_artists_and_reassigns_versions(self):
        antonio = Artist.objects.create(name='Antonio Carlos Jobim')
        tom = Artist.objects.create(name='Tom Jobim')
        chico = Artist.objects.create(name='Chico Buarque')
        vinicius = Artist.objects.create(name='Vinicius de Moraes')

        first_song = Song.objects.create(
            name='Olha Maria',
            version=1,
            artist_text='Antonio Carlos Jobim, Chico Buarque, Vinicius de Moraes',
            file='brasileiro-songs/olha-maria-1.pdf',
            storage_key='brasileiro-songs/olha-maria-1.pdf',
        )
        first_song.artist.add(antonio, chico, vinicius)

        second_song = Song.objects.create(
            name='Olha Maria',
            version=1,
            artist_text='Tom Jobim, Vinicius de Moraes, Chico Buarque',
            file='brasileiro-songs/olha-maria-2.pdf',
            storage_key='brasileiro-songs/olha-maria-2.pdf',
        )
        second_song.artist.add(tom, vinicius, chico)

        with NamedTemporaryFile(mode="w+", suffix=".json") as alias_file:
            json.dump({"Tom Jobim": "Antônio Carlos Jobim", "Antonio Carlos Jobim": "Antônio Carlos Jobim"}, alias_file)
            alias_file.flush()
            call_command('normalize_song_catalog', artist_alias_json=alias_file.name)

        normalized_songs = list(
            Song.objects.prefetch_related('artist').order_by('version', 'id')
        )

        self.assertEqual([song.version for song in normalized_songs], [1, 2])
        self.assertEqual(
            {song.artist_text for song in normalized_songs},
            {'Antônio Carlos Jobim, Chico Buarque, Vinicius de Moraes'},
        )
        self.assertFalse(Artist.objects.filter(name='Tom Jobim').exists())
        self.assertTrue(Artist.objects.filter(name='Antônio Carlos Jobim').exists())

    @patch('songAPI.songs.management.commands.normalize_song_catalog.build_title_alias_map_with_llm')
    @patch('songAPI.songs.management.commands.normalize_song_catalog.build_artist_alias_map_with_llm')
    def test_normalize_song_catalog_merges_title_variants_with_llm(
        self,
        mock_build_artist_alias_map,
        mock_build_title_alias_map,
    ):
        jobim = Artist.objects.create(name='Antônio Carlos Jobim')
        vinicius = Artist.objects.create(name='Vinicius de Moraes')

        first_song = Song.objects.create(
            name='Amor em paz',
            version=1,
            artist_text='Antônio Carlos Jobim, Vinicius de Moraes',
            file='brasileiro-songs/amor-em-paz-1.pdf',
            storage_key='brasileiro-songs/amor-em-paz-1.pdf',
        )
        first_song.artist.add(jobim, vinicius)

        second_song = Song.objects.create(
            name='Amor em Paz',
            version=1,
            artist_text='Vinicius de Moraes, Antônio Carlos Jobim',
            file='brasileiro-songs/amor-em-paz-2.pdf',
            storage_key='brasileiro-songs/amor-em-paz-2.pdf',
        )
        second_song.artist.add(vinicius, jobim)

        mock_build_artist_alias_map.return_value = {
            'Antônio Carlos Jobim': 'Antônio Carlos Jobim',
            'Vinicius de Moraes': 'Vinicius de Moraes',
        }
        mock_build_title_alias_map.return_value = {
            ('Amor em paz', 'Antônio Carlos Jobim, Vinicius de Moraes'): 'Amor em Paz',
            ('Amor em Paz', 'Antônio Carlos Jobim, Vinicius de Moraes'): 'Amor em Paz',
        }

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            call_command('normalize_song_catalog', with_llm=True)

        normalized_songs = list(
            Song.objects.prefetch_related('artist').order_by('version', 'id')
        )

        self.assertEqual([song.version for song in normalized_songs], [1, 2])
        self.assertEqual({song.name for song in normalized_songs}, {'Amor em Paz'})
        self.assertEqual(
            {song.artist_text for song in normalized_songs},
            {'Antônio Carlos Jobim, Vinicius de Moraes'},
        )
