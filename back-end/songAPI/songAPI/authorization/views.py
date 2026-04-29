from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User
from django.middleware.csrf import get_token
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from songAPI.authorization.serializers import (
    AuthenticatedUserSerializer,
    AuthenticatedUserResponseSerializer,
    CsrfTokenSerializer,
    GroupSerializer,
    LoginSerializer,
    LoginResponseSerializer,
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


class CsrfTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: CsrfTokenSerializer},
        tags=['auth'],
    )
    def get(self, request):
        return Response({'csrfToken': get_token(request)})


csrf_token = CsrfTokenView.as_view()
