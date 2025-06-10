from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from songAPI.songs.models import Song
from songAPI.songs.serializers import SongSerializer

# Create your views here.
@api_view(['GET', 'POST'])
def song_list(request):
  """
  List all songs
  """
  if request.method == 'GET':
    songs = Song.objects.all()
    serializer = SongSerializer(songs, many = True)
    return Response(serializer.data)

  elif request.method == 'POST':
    serializer = SongSerializer(data=request.data)
    if serializer.is_valid():
      serializer.save()
      return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)