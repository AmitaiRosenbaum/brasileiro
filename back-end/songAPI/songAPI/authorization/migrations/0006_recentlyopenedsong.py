from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authorization', '0005_playlist_song_order'),
        ('songs', '0010_song_search_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecentlyOpenedSong',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('opened_at', models.DateTimeField(auto_now=True)),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='songs.song')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recently_opened_songs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-opened_at']},
        ),
        migrations.AddConstraint(
            model_name='recentlyopenedsong',
            constraint=models.UniqueConstraint(fields=('user', 'song'), name='unique_recent_song_per_user'),
        ),
        migrations.AddIndex(
            model_name='recentlyopenedsong',
            index=models.Index(fields=['user', '-opened_at'], name='recent_song_user_time_idx'),
        ),
    ]
