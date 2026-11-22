from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.middleware.csrf import get_token
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from songAPI.authorization.models import Playlist
from songAPI.authorization.serializers import (
    AuthenticatedUserSerializer,
    AuthenticatedUserResponseSerializer,
    CsrfTokenSerializer,
    CurrentUserUpdateResponseSerializer,
    CurrentUserUpdateSerializer,
    GroupSerializer,
    LoginSerializer,
    LoginResponseSerializer,
    PlaylistSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Playlist.objects
            .filter(Q(user=self.request.user) | Q(members=self.request.user))
            .select_related('user')
            .prefetch_related('songs', 'members')
            .distinct()
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        playlist = self.get_object()
        if playlist.user_id != request.user.id:
            return Response(
                {'detail': 'Only the playlist owner can delete it.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if playlist.is_liked_songs:
            return Response(
                {'detail': 'The default liked songs playlist cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='members')
    def add_member(self, request, pk=None):
        playlist = self.get_object()
        if playlist.user_id != request.user.id:
            return Response(
                {'detail': 'Only the playlist owner can manage sharing.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if playlist.is_liked_songs:
            return Response(
                {'detail': 'Liked Songs cannot be shared.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = str(request.data.get('username', '')).strip()
        if not username:
            return Response(
                {'username': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            member = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            return Response(
                {'username': ['No user with that username exists.']},
                status=status.HTTP_404_NOT_FOUND,
            )
        if member.id == request.user.id:
            return Response(
                {'username': ['The owner already has access.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        playlist.members.add(member)
        return Response(self.get_serializer(playlist).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'members/(?P<user_id>\d+)',
    )
    def remove_member(self, request, pk=None, user_id=None):
        playlist = self.get_object()
        if playlist.user_id != request.user.id:
            return Response(
                {'detail': 'Only the playlist owner can manage sharing.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        playlist.members.remove(user_id)
        return Response(self.get_serializer(playlist).data, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description='Invalid username or password.'),
        },
        tags=['auth'],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        if user is None:
            return Response({'detail': 'Invalid username or password.'}, status=400)

        login(request, user)

        return Response({
            'user': AuthenticatedUserSerializer(user).data,
            'csrfToken': get_token(request),
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description='User logged out successfully.')},
        tags=['auth'],
    )
    def post(self, request):
        logout(request)
        return Response(status=204)


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: AuthenticatedUserResponseSerializer},
        tags=['auth'],
    )
    def get(self, request):
        return Response({'user': AuthenticatedUserSerializer(request.user).data})

    @extend_schema(
        request=CurrentUserUpdateSerializer,
        responses={200: CurrentUserUpdateResponseSerializer},
        tags=['auth'],
    )
    def patch(self, request):
        serializer = CurrentUserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'user': AuthenticatedUserSerializer(request.user).data})


class CsrfTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: CsrfTokenSerializer},
        tags=['auth'],
    )
    def get(self, request):
        return Response({'csrfToken': get_token(request)})


csrf_token = CsrfTokenView.as_view()
