import boto3
from songAPI.songs.models import Song, Artist
from songAPI.songs.serializers import SongSerializer, ArtistSerializer
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema
from songAPI.songs.models import extended_song_params
from django.conf import settings
from botocore.config import Config


def parse_song_file_metadata(file_name):
    stem = file_name.rsplit('.', 1)[0]

    if '_' in stem:
        title, artists_combined = stem.split('_', 1)
        artists = [artist.strip() for artist in artists_combined.split(' e ') if artist.strip()]
    else:
        title = stem
        artists = []

    return title, artists


def get_or_create_song_for_file(file_name, title, artist_names):
    song = Song.objects.filter(file=file_name).prefetch_related('artist').first()
    if song is not None:
        return song

    existing_versions = Song.objects.filter(name=title).values_list('version', flat=True)
    next_version = max(existing_versions, default=0) + 1

    song = Song.objects.create(
        name=title,
        version=next_version,
        file=file_name,
    )
    for artist_name in artist_names:
        artist, _created = Artist.objects.get_or_create(name=artist_name)
        song.artist.add(artist)

    return song


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
    file_name = request.query_params['key']
    b2 = boto3.resource(
        service_name='s3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )

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
    b2 = boto3.resource(
        service_name='s3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )

    if b2.meta is None:
        return Response({'message': 'unable to connect to B2 bucket'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    bucket = b2.Bucket(settings.AWS_STORAGE_BUCKET_NAME)

    songs = []
    for obj in bucket.objects.all():
        file_name = obj.key
        title, artist_names = parse_song_file_metadata(file_name)
        song = get_or_create_song_for_file(file_name, title, artist_names)

        songs.append({
            'id': song.id,
            'title': title,
            'artists': artist_names,
            'key': file_name,
        })

    return Response({'data': songs}, status=status.HTTP_200_OK)
