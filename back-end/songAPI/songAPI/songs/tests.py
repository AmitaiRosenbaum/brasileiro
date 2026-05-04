from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from io import BytesIO
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
        self.assertEqual(response.data['data'][0]['artists'], ['Chico Buarque'])

    def test_get_all_songs_artist_mode_sections_by_last_name(self):
        self.client.force_authenticate(user=self.user)
        tom = Artist.objects.create(name='Tom Jobim')
        chico = Artist.objects.create(name='Chico Buarque')
        for artist in [tom, chico]:
            song = Song.objects.create(
                name=f'{artist.name} song',
                version=1,
                artist_text=artist.name,
                file=f'brasileiro-songs/{artist.id}.pdf',
                storage_key=f'brasileiro-songs/{artist.id}.pdf',
            )
            song.artist.add(artist)

        response = self.client.get(
            '/songs/getAllSongs',
            {'mode': 'artist', 'section': 'J', 'page_size': 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pagination']['sections'], ['B', 'J'])
        self.assertEqual(response.data['pagination']['total'], 1)
        self.assertEqual(response.data['data'][0]['artists'], ['Tom Jobim'])

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

    def test_update_song_metadata_updates_group_database_and_manifest(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='Tom Jobim')
        songs = []
        for version in [1, 2]:
            song = Song.objects.create(
                name='Wave',
                version=version,
                artist_text='Tom Jobim',
                file=f'brasileiro-songs/wave__tom-jobim__v{version:02d}.pdf',
                storage_key=f'brasileiro-songs/wave__tom-jobim__v{version:02d}.pdf',
            )
            song.artist.add(artist)
            songs.append(song)

        manifest = (
            'index,source_file,final_file,title,artist,version,song_key,title_slug,artist_slug\n'
            '0,wave-a.pdf,wave__tom-jobim__v01.pdf,Wave,Tom Jobim,1,wave__tom-jobim,wave,tom-jobim\n'
            '1,wave-b.pdf,wave__tom-jobim__v02.pdf,Wave,Tom Jobim,2,wave__tom-jobim,wave,tom-jobim\n'
        )
        mock_client = MagicMock()
        mock_client.get_object.return_value = {'Body': BytesIO(manifest.encode('utf-8'))}

        with patch('songAPI.songs.views.boto3.client', return_value=mock_client):
            response = self.client.patch(
                f'/songs/{songs[0].id}/metadata',
                {'title': 'Vou Te Contar', 'artist': 'Antônio Carlos Jobim'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['manifest_rows_updated'], 2)
        self.assertEqual(
            set(Song.objects.values_list('name', flat=True)),
            {'Vou Te Contar'},
        )
        self.assertEqual(
            set(Song.objects.values_list('artist_text', flat=True)),
            {'Antônio Carlos Jobim'},
        )
        self.assertEqual(Artist.objects.filter(name='Antônio Carlos Jobim').count(), 1)
        self.assertFalse(Artist.objects.filter(name='Tom Jobim').exists())

        put_kwargs = mock_client.put_object.call_args.kwargs
        self.assertEqual(put_kwargs['Key'], 'brasileiro-songs/manifest.csv')
        written_manifest = put_kwargs['Body'].decode('utf-8')
        self.assertIn('Vou Te Contar,Antônio Carlos Jobim', written_manifest)
        self.assertNotIn('Wave,Tom Jobim', written_manifest)

    def test_update_song_metadata_merges_into_existing_song_group_as_new_version(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_authenticate(user=self.user)
        artist = Artist.objects.create(name='Tom Jobim')
        existing_song = Song.objects.create(
            name='Triste',
            version=1,
            artist_text='Tom Jobim',
            file='brasileiro-songs/triste__tom-jobim__v01.pdf',
            storage_key='brasileiro-songs/triste__tom-jobim__v01.pdf',
        )
        source_song = Song.objects.create(
            name='Triste, Triste',
            version=1,
            artist_text='Tom Jobim',
            file='brasileiro-songs/triste-triste__tom-jobim__v01.pdf',
            storage_key='brasileiro-songs/triste-triste__tom-jobim__v01.pdf',
        )
        existing_song.artist.add(artist)
        source_song.artist.add(artist)

        manifest = (
            'index,source_file,final_file,title,artist,version,song_key,title_slug,artist_slug\n'
            '0,triste.pdf,triste__tom-jobim__v01.pdf,Triste,Tom Jobim,1,triste__tom-jobim,triste,tom-jobim\n'
            '1,triste-triste.pdf,triste-triste__tom-jobim__v01.pdf,"Triste, Triste",Tom Jobim,1,triste-triste__tom-jobim,triste-triste,tom-jobim\n'
        )
        mock_client = MagicMock()
        mock_client.get_object.return_value = {'Body': BytesIO(manifest.encode('utf-8'))}

        with patch('songAPI.songs.views.boto3.client', return_value=mock_client):
            response = self.client.patch(
                f'/songs/{source_song.id}/metadata',
                {'title': 'Triste'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['title'], 'Triste')
        self.assertEqual(
            list(Song.objects.filter(name='Triste').order_by('version').values_list('id', 'version')),
            [(existing_song.id, 1), (source_song.id, 2)],
        )

        written_manifest = mock_client.put_object.call_args.kwargs['Body'].decode('utf-8')
        self.assertIn('triste-triste__tom-jobim__v01.pdf,Triste,Tom Jobim,2', written_manifest)

    def test_update_song_metadata_rejects_blank_title(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_authenticate(user=self.user)
        song = Song.objects.create(
            name='Wave',
            version=1,
            artist_text='Tom Jobim',
            file='brasileiro-songs/wave.pdf',
            storage_key='brasileiro-songs/wave.pdf',
        )

        response = self.client.patch(
            f'/songs/{song.id}/metadata',
            {'title': '  '},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_update_song_metadata_requires_staff(self):
        self.client.force_authenticate(user=self.user)
        song = Song.objects.create(
            name='Wave',
            version=1,
            artist_text='Tom Jobim',
            file='brasileiro-songs/wave.pdf',
            storage_key='brasileiro-songs/wave.pdf',
        )

        response = self.client.patch(
            f'/songs/{song.id}/metadata',
            {'title': 'Vou Te Contar'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

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
