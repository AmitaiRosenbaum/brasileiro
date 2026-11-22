from django.contrib.auth.models import Group, User
from django.db.models import Q
from songAPI.authorization.models import Playlist, Profile
from songAPI.songs.models import Artist, Book, Song
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


class PlaylistUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    def get_display_name(self, user):
        return user.get_full_name().strip() or user.username

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']


class PlaylistSerializer(serializers.ModelSerializer):
    songs = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Playlist.songs.field.related_model.objects.all(),
        required=False,
    )
    owner = PlaylistUserSerializer(source='user', read_only=True)
    members = PlaylistUserSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, playlist):
        viewer = self.context.get('viewer')
        if viewer is None:
            request = self.context.get('request')
            viewer = getattr(request, 'user', None)
        return bool(viewer and viewer.is_authenticated and playlist.user_id == viewer.id)

    class Meta:
        model = Playlist
        fields = [
            'id',
            'name',
            'songs',
            'is_liked_songs',
            'owner',
            'members',
            'is_owner',
        ]
        read_only_fields = ['id', 'is_liked_songs', 'owner', 'members', 'is_owner']

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
    playlists = serializers.SerializerMethodField()
    catalogue_stats = serializers.SerializerMethodField()

    def get_catalogue_stats(self, _user):
        return {
            'songs': Song.objects.values('name', 'artist_text').distinct().count(),
            'artists': Artist.objects.count(),
            'books': Book.objects.count(),
        }

    def get_playlists(self, user):
        playlists = (
            Playlist.objects
            .filter(Q(user=user) | Q(members=user))
            .select_related('user')
            .prefetch_related('songs', 'members')
            .distinct()
        )
        return PlaylistSerializer(
            playlists,
            many=True,
            context={**self.context, 'viewer': user},
        ).data

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'playlists',
            'catalogue_stats',
        ]


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
