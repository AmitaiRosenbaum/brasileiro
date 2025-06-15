import boto3
from songAPI.songs.models import Song
from songAPI.songs.serializers import SongSerializer
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema
from songAPI.songs.models import extended_song_params
from django.conf import settings
from botocore.config import Config


class SongList(generics.ListCreateAPIView):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class SongDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


"""
Get pre-signed AWS S3 URL to access sheet music
"""


@extend_schema(parameters=extended_song_params)
@api_view(['GET'])
def get_song_url(request):
    name = request.query_params['name']
    file_name = name + '.pdf'
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

    objs = bucket.objects.all()
    songs = []
    for obj in objs:
        file_name = obj.key
        print(file_name)
        if '_' in file_name:
            title, artists_combined = file_name[:-4].split('_')
            artists = artists_combined.split(' e ')
        else:
            title = file_name[:-4]
            artists = []
        songs.append({
            'title': title,
            'artist': artists
        })

    return Response({'url': songs}, status=status.HTTP_200_OK)
