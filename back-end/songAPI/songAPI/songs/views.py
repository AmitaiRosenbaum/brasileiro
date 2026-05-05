import boto3
import csv
import random
import unicodedata
from io import StringIO
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.db.models import Q
from songAPI.songs.models import Book, Song, Artist
from songAPI.songs.serializers import BookSerializer, SongSerializer, ArtistSerializer
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


def build_b2_client():
    return boto3.client(
        service_name='s3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )


def build_manifest_key():
    prefix = settings.B2_SONGS_PREFIX.strip('/')
    if not prefix:
        return 'manifest.csv'
    return f'{prefix}/manifest.csv'


def manifest_final_file_for_song(song):
    storage_key = get_song_storage_key(song)
    prefix = settings.B2_SONGS_PREFIX.strip('/')
    prefix_with_slash = f'{prefix}/' if prefix else ''
    if prefix_with_slash and storage_key.startswith(prefix_with_slash):
        return storage_key[len(prefix_with_slash):]
    return storage_key.rsplit('/', 1)[-1]


def read_manifest(client, bucket, key):
    response = client.get_object(Bucket=bucket, Key=key)
    body = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(StringIO(body))
    rows = list(reader)
    fieldnames = reader.fieldnames or []
    return fieldnames, rows


def write_manifest(client, bucket, key, fieldnames, rows):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=output.getvalue().encode('utf-8'),
        ContentType='text/csv',
    )


def artist_names_from_text(artist_text):
    return [
        artist.strip()
        for artist in artist_text.replace(' and ', ' e ').split(',')
        for artist in artist.split(' e ')
        if artist.strip()
    ]


def reassign_song_group_versions(source_song_ids, title, artist_text, artists):
    source_songs = list(
        Song.objects
        .select_for_update()
        .filter(pk__in=source_song_ids)
        .order_by('version', 'id')
    )
    existing_target_songs = list(
        Song.objects
        .select_for_update()
        .filter(name=title, artist_text=artist_text)
        .exclude(pk__in=source_song_ids)
        .order_by('version', 'id')
    )
    ordered_songs = [*existing_target_songs, *source_songs]
    source_song_id_set = set(source_song_ids)

    for song in ordered_songs:
        changed_fields = ['version']
        song.version = 1_000_000 + song.pk
        if song.pk in source_song_id_set:
            song.name = title
            song.artist_text = artist_text
            changed_fields.extend(['name', 'artist_text'])
        song.save(update_fields=changed_fields)

    version_by_song_id = {}
    for version, song in enumerate(ordered_songs, start=1):
        song.version = version
        song.save(update_fields=['version'])
        version_by_song_id[song.pk] = version
        if song.pk in source_song_id_set:
            song.artist.set(artists)

    return version_by_song_id


def serialize_song_version(song):
    artists = [artist.name for artist in song.artist.all()]
    book = serialize_book(song.book)
    return {
        'id': song.id,
        'version': song.version,
        'key': get_song_storage_key(song),
        'title': song.name,
        'artists': artists,
        'book': book,
        'book_title': book['title'] if book else '',
        'book_song_index': song.book_song_index,
    }


def serialize_book(book):
    if book is None:
        return None

    cover_image_url = ''
    if book.cover_image:
        try:
            cover_image_url = book.cover_image.url
        except ValueError:
            cover_image_url = ''

    return {
        'id': book.id,
        'title': book.title,
        'cover_image': cover_image_url,
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


def parse_bool(value):
    return str(value).casefold() in ['1', 'true', 'yes', 'on']


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
            get_artist_sort_value(song['artists'][0]).casefold(),
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


def normalize_search_text(value):
    return normalize_index_text(value).casefold()


def song_search_values(song):
    book_titles = [
        version.get('book_title', '')
        for version in song.get('versions', [])
    ]
    return [
        song['title'],
        ', '.join(song['artists']),
        ', '.join(book_titles),
    ]


def song_matches_search(song, search):
    normalized_search = normalize_search_text(search)
    search_terms = normalized_search.split()
    normalized_values = [
        normalize_search_text(value)
        for value in song_search_values(song)
        if value
    ]

    if any(normalized_search in value for value in normalized_values):
        return True

    return bool(search_terms) and all(
        any(term in value for value in normalized_values)
        for term in search_terms
    )


def get_search_rank(song, search):
    normalized_search = normalize_search_text(search)
    search_terms = normalized_search.split()
    title = normalize_search_text(song['title'])
    artists = normalize_search_text(', '.join(song['artists']))

    if title.startswith(normalized_search):
        return 0
    if artists.startswith(normalized_search):
        return 1
    if normalized_search in title:
        return 2
    if normalized_search in artists:
        return 3
    if search_terms and all(term in title for term in search_terms):
        return 4
    return 5


def filter_and_sort_songs_by_search(song_results, search):
    matched_songs = [
        song for song in song_results
        if song_matches_search(song, search)
    ]

    return sorted(
        matched_songs,
        key=lambda song: (
            get_search_rank(song, search),
            normalize_search_text(song['title']),
            normalize_search_text(', '.join(song['artists'])),
            song['id'],
        ),
    )


def get_index_letter(value):
    normalized_value = normalize_index_text(value)
    for character in normalized_value:
        if character.isalpha():
            return character.upper()
        if character.isdigit():
            return '#'
    return '#'


def get_artist_sort_value(artist):
    normalized_artist = normalize_index_text(artist)
    name_parts = normalized_artist.split()
    return name_parts[-1] if name_parts else ''


def get_song_section(song, mode):
    if mode == 'artist':
        artist = song['artists'][0] if song['artists'] else ''
        return get_index_letter(get_artist_sort_value(artist))
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
    pagination_class = None


class BookList(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    pagination_class = None


@api_view(['GET'])
def get_book_songs(request, pk):
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        return Response({'message': 'book not found'}, status=status.HTTP_404_NOT_FOUND)

    songs = (
        Song.objects
        .select_related('book')
        .prefetch_related('artist')
        .filter(book=book)
        .order_by('book_song_index', 'name', 'id')
    )
    return Response(
        {
            'book': serialize_book(book),
            'data': [serialize_song_version(song) for song in songs],
        },
        status=status.HTTP_200_OK,
    )


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
            .select_related('book')
            .prefetch_related('artist')
            .filter(name=selected_song.name, artist_text=selected_song.artist_text)
            .order_by('name', 'artist_text', 'version', 'id')
        )
        grouped_songs = get_grouped_songs(query)
        return Response({'data': grouped_songs}, status=status.HTTP_200_OK)

    should_paginate = any(
        param in request.query_params
        for param in ['mode', 'page', 'page_size', 'search', 'random']
    )
    mode = request.query_params.get('mode', 'title')
    search = request.query_params.get('search', '').strip()
    should_randomize = parse_bool(request.query_params.get('random', False))
    section = request.query_params.get('section', '').strip()
    page = parse_positive_int(request.query_params.get('page'), 1)
    page_size = parse_positive_int(request.query_params.get('page_size'), 50, 100)

    query = (
        Song.objects
        .select_related('book')
        .prefetch_related('artist')
        .order_by('name', 'artist_text', 'version', 'id')
    )

    grouped_songs = get_grouped_songs(query)
    if not should_paginate:
        return Response({'data': grouped_songs}, status=status.HTTP_200_OK)

    song_results = expand_songs_by_artist(grouped_songs) if mode == 'artist' else grouped_songs
    if search:
        song_results = filter_and_sort_songs_by_search(song_results, search)
    elif should_randomize:
        random.shuffle(song_results)

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


@api_view(['PATCH'])
def update_song_metadata(request, pk):
    if not request.user.is_staff:
        return Response({'message': 'staff access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        selected_song = Song.objects.get(pk=pk)
    except Song.DoesNotExist:
        return Response({'message': 'song not found'}, status=status.HTTP_404_NOT_FOUND)

    title = request.data.get('title')
    artist_text = request.data.get('artist')
    if title is None and artist_text is None:
        return Response(
            {'message': 'title or artist is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    title = selected_song.name if title is None else str(title).strip()
    artist_text = (
        selected_song.artist_text
        if artist_text is None
        else str(artist_text).strip()
    )
    if not title or not artist_text:
        return Response(
            {'message': 'title and artist cannot be blank'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    group_query = Song.objects.filter(
        name=selected_song.name,
        artist_text=selected_song.artist_text,
    ).order_by('version', 'id')
    group_songs = list(group_query)
    final_files = {manifest_final_file_for_song(song) for song in group_songs}
    manifest_key = build_manifest_key()
    client = build_b2_client()

    try:
        fieldnames, manifest_rows = read_manifest(
            client,
            settings.AWS_STORAGE_BUCKET_NAME,
            manifest_key,
        )
    except Exception as error:
        return Response(
            {'message': f'unable to read manifest: {error}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    missing_fields = {'title', 'artist', 'final_file'} - set(fieldnames)
    if missing_fields:
        missing_field_text = ", ".join(sorted(missing_fields))
        return Response(
            {'message': f'manifest is missing required columns: {missing_field_text}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    updated_manifest_count = 0
    manifest_version_by_final_file = {}
    for row in manifest_rows:
        if row.get('final_file') in final_files:
            row['title'] = title
            row['artist'] = artist_text
            updated_manifest_count += 1

    if updated_manifest_count != len(final_files):
        return Response(
            {
                'message': 'manifest rows did not match every song version',
                'matched_manifest_rows': updated_manifest_count,
                'expected_versions': len(final_files),
            },
            status=status.HTTP_409_CONFLICT,
        )

    try:
        with transaction.atomic():
            artists = []
            for artist_name in artist_names_from_text(artist_text):
                artist, _created = Artist.objects.get_or_create(name=artist_name)
                artists.append(artist)

            version_by_song_id = reassign_song_group_versions(
                [song.pk for song in group_songs],
                title,
                artist_text,
                artists,
            )
            for song in group_songs:
                manifest_version_by_final_file[manifest_final_file_for_song(song)] = (
                    version_by_song_id[song.pk]
                )

            for row in manifest_rows:
                row_version = manifest_version_by_final_file.get(row.get('final_file'))
                if row_version is not None and 'version' in fieldnames:
                    row['version'] = row_version

            Artist.objects.filter(song__isnull=True).delete()

            write_manifest(
                client,
                settings.AWS_STORAGE_BUCKET_NAME,
                manifest_key,
                fieldnames,
                manifest_rows,
            )
    except Exception as error:
        return Response(
            {'message': f'unable to update song metadata: {error}'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    updated_group = Song.objects.filter(name=title, artist_text=artist_text)
    return Response(
        {
            'data': serialize_song_group(
                list(updated_group.prefetch_related('artist').order_by('version', 'id'))
            ),
            'manifest_rows_updated': updated_manifest_count,
        },
        status=status.HTTP_200_OK,
    )
