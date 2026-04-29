from django.contrib.auth.models import Group, User
from songAPI.authorization.models import Profile
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['artists', 'songs']


class AuthenticatedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, style={'input_type': 'password'})


class CsrfTokenSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()


class AuthenticatedUserResponseSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()


class LoginResponseSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()
    csrfToken = serializers.CharField()
