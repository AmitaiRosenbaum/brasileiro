from django.urls import path
from songAPI.songs import views

urlpatterns = [
    path('songs/', views.SongList.as_view()),
    path('songs/<int:pk>', views.SongDetail.as_view()),
    path('songs/<int:pk>/metadata', views.update_song_metadata),
    path('songs/getSongUrl', views.get_song_url),
    path('songs/getAllSongs', views.get_all_available_songs),
    path('songs/artist/', views.ArtistList.as_view()),
    path('songs/books/', views.BookList.as_view()),
    path('songs/books/<int:pk>/songs', views.get_book_songs),
]
