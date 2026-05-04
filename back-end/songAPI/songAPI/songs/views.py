import boto3
import unicodedata
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from songAPI.songs.models import Song, Artist
from songAPI.songs.serializers import SongSerializer, ArtistSerializer
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema
from songAPI.songs.models import extended_song_params
from django.conf import settings
from botocore.config import Config


def get_song_storage_key(song):
    if song.storage_key:
        return song.storage_key
    return song.file.name


def build_b2_resource():
    return boto3.resource(
        service_name='s3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )


def serialize_song_version(song):
    artists = [artist.name for artist in song.artist.all()]
    return {
        'id': song.id,
        'version': song.version,
        'key': get_song_storage_key(song),
        'title': song.name,
        'artists': artists,
    }


def serialize_song_group(songs):
    versions = [serialize_song_version(song) for song in songs]
    primary = versions[0]
    return {
        'id': primary['id'],
        'title': primary['title'],
        'artists': primary['artists'],
        'key': primary['key'],
        'version': primary['version'],
        'versions': versions,
    }


def parse_positive_int(value, default, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    parsed = max(parsed, 1)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def get_grouped_songs(query):
    grouped_songs = []
    current_group_key = None
    current_group = []

    for song in query:
        group_key = (song.name, song.artist_text)
        if current_group_key is not None and group_key != current_group_key:
            grouped_songs.append(serialize_song_group(current_group))
            current_group = []
        current_group_key = group_key
        current_group.append(song)

    if current_group:
        grouped_songs.append(serialize_song_group(current_group))

    return grouped_songs


def expand_songs_by_artist(song_groups):
    expanded_songs = []

    for song in song_groups:
        artists = song['artists'] or ['Unknown artist']
        for artist in artists:
            expanded_song = {**song, 'artists': [artist]}
            expanded_songs.append(expanded_song)

    return sorted(
        expanded_songs,
        key=lambda song: (
            song['artists'][0].casefold(),
            song['title'].casefold(),
            song['id'],
        ),
    )


def normalize_index_text(value):
    return ''.join(
        character
        for character in unicodedata.normalize('NFD', value.strip())
        if unicodedata.category(character) != 'Mn'
    )


def get_index_letter(value):
    normalized_value = normalize_index_text(value)
    for character in normalized_value:
        if character.isalpha():
            return character.upper()
        if character.isdigit():
            return '#'
    return '#'


def get_song_section(song, mode):
    if mode == 'artist':
        return get_index_letter(song['artists'][0] if song['artists'] else '')
    return get_index_letter(song['title'])


def get_available_sections(song_results, mode):
    return sorted(
        {get_song_section(song, mode) for song in song_results},
        key=lambda section: (section != '#', section),
    )


def filter_songs_by_section(song_results, mode, section):
    if not section:
        return song_results

    normalized_section = section.upper()
    return [
        song for song in song_results
        if get_song_section(song, mode) == normalized_section
    ]


class ArtistList(generics.ListCreateAPIView):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer


class SongList(generics.ListCreateAPIView):
    queryset = Song.objects.all()
    serializer_class = SongSerializer

    def create(self, request, *args, **kwargs):
        create_bulk = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=create_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SongDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


"""
Get pre-signed AWS S3 URL to access sheet music
"""


@extend_schema(parameters=extended_song_params)
@api_view(['GET'])
def get_song_url(request):
    song_id = request.query_params.get('id')
    file_name = request.query_params.get('key')
    if song_id:
        try:
            song = Song.objects.get(pk=song_id)
        except Song.DoesNotExist:
            return Response({'message': 'song not found'}, status=status.HTTP_404_NOT_FOUND)
        file_name = get_song_storage_key(song)
    elif not file_name:
        return Response({'message': 'id or key is required'}, status=status.HTTP_400_BAD_REQUEST)

    b2 = build_b2_resource()

    if b2.meta is None:
        return Response({'message': 'unable to connect to B2 bucket'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    url = b2.meta.client.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': file_name
        }
    )

    return Response({'url': url})


"""
Get pre-signed AWS S3 URL to access sheet music
"""


@api_view(['GET'])
def get_all_available_songs(request):
    song_id = request.query_params.get('id')
    song_key = request.query_params.get('key')
    if song_id or song_key:
        try:
            if song_id:
                selected_song = Song.objects.get(pk=song_id)
            else:
                selected_song = Song.objects.get(Q(storage_key=song_key) | Q(file=song_key))
        except (ValueError, Song.DoesNotExist):
            return Response({'message': 'song not found'}, status=status.HTTP_404_NOT_FOUND)

        query = (
            Song.objects
            .prefetch_related('artist')
            .filter(name=selected_song.name, artist_text=selected_song.artist_text)
            .order_by('name', 'artist_text', 'version', 'id')
        )
        grouped_songs = get_grouped_songs(query)
        return Response({'data': grouped_songs}, status=status.HTTP_200_OK)

    should_paginate = any(
        param in request.query_params for param in ['mode', 'page', 'page_size', 'search']
    )
    mode = request.query_params.get('mode', 'title')
    search = request.query_params.get('search', '').strip()
    section = request.query_params.get('section', '').strip()
    page = parse_positive_int(request.query_params.get('page'), 1)
    page_size = parse_positive_int(request.query_params.get('page_size'), 50, 100)

    query = (
        Song.objects
        .prefetch_related('artist')
        .order_by('name', 'artist_text', 'version', 'id')
    )

    if search:
        query = query.filter(
            Q(name__icontains=search)
            | Q(artist_text__icontains=search)
            | Q(artist__name__icontains=search)
        ).distinct()

    grouped_songs = get_grouped_songs(query)
    if not should_paginate:
        return Response({'data': grouped_songs}, status=status.HTTP_200_OK)

    song_results = expand_songs_by_artist(grouped_songs) if mode == 'artist' else grouped_songs
    sections = get_available_sections(song_results, mode)
    song_results = filter_songs_by_section(song_results, mode, section)

    paginator = Paginator(song_results, page_size)
    try:
        paged_songs = paginator.page(page)
    except EmptyPage:
        paged_songs = paginator.page(paginator.num_pages or 1)

    return Response(
        {
            'data': list(paged_songs.object_list),
            'pagination': {
                'page': paged_songs.number,
                'page_size': page_size,
                'total': paginator.count,
                'total_pages': paginator.num_pages,
                'has_next': paged_songs.has_next(),
                'has_previous': paged_songs.has_previous(),
                'sections': sections,
            },
        },
        status=status.HTTP_200_OK,
    )
