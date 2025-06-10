from django.urls import path
from songAPI.songs import views

urlpatterns = [
  path('songs/', views.song_list)
] 