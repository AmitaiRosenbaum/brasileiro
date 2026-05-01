from django.contrib.auth.models import Group, User
from songAPI.authorization.models import Playlist, Profile
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


class PlaylistSerializer(serializers.ModelSerializer):
    songs = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Playlist.songs.field.related_model.objects.all(),
        required=False,
    )

    class Meta:
        model = Playlist
        fields = ['id', 'name', 'songs', 'is_liked_songs']
        read_only_fields = ['id', 'is_liked_songs']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        song_ids = list(instance.songs.values_list('id', flat=True))
        ordered_song_ids = [
            song_id for song_id in instance.song_order if song_id in song_ids
        ]
        missing_song_ids = [song_id for song_id in song_ids if song_id not in ordered_song_ids]
        representation['songs'] = ordered_song_ids + missing_song_ids
        return representation

    def create(self, validated_data):
        songs = validated_data.pop('songs', [])
        playlist = super().create(validated_data)
        if songs:
            playlist.songs.set(songs)
            playlist.song_order = [song.id for song in songs]
            playlist.save(update_fields=['song_order'])
        return playlist

    def update(self, instance, validated_data):
        songs = validated_data.pop('songs', None)
        playlist = super().update(instance, validated_data)
        if songs is not None:
            playlist.songs.set(songs)
            playlist.song_order = [song.id for song in songs]
            playlist.save(update_fields=['song_order'])
        return playlist


class AuthenticatedUserSerializer(serializers.ModelSerializer):
    playlists = PlaylistSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'playlists']


class CurrentUserUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, style={'input_type': 'password'})


class CsrfTokenSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()


class AuthenticatedUserResponseSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()


class CurrentUserUpdateResponseSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()


class LoginResponseSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()
    csrfToken = serializers.CharField()
