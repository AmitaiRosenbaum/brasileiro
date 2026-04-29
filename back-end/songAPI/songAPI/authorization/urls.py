from django.urls import path

from songAPI.authorization import views

urlpatterns = [
    path('csrf/', views.csrf_token, name='auth-csrf'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('me/', views.CurrentUserView.as_view(), name='auth-me'),
]
