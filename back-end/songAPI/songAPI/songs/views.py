import boto3
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
    query = (
        Song.objects
        .prefetch_related('artist')
        .order_by('name', 'artist_text', 'version', 'id')
    )
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

    return Response({'data': grouped_songs}, status=status.HTTP_200_OK)
