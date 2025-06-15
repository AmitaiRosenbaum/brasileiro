from django.urls import path
from songAPI.songs import views

urlpatterns = [
    path('songs/', views.SongList.as_view()),
    path('songs/<int:pk>', views.SongDetail.as_view()),
    path('songs/getSongUrl', views.get_song_url),
    path('songs/getAllSongs', views.get_all_available_songs)
]
