from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('songs', '0010_song_search_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='SongMetadataOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('storage_key', models.CharField(max_length=500, unique=True)),
                ('book_title', models.CharField(blank=True, max_length=255)),
                ('book_song_index', models.PositiveIntegerField(blank=True, null=True)),
                ('title', models.CharField(max_length=100)),
                ('artist_text', models.CharField(max_length=255)),
                ('version', models.PositiveIntegerField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('song', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='metadata_overrides', to='songs.song')),
            ],
            options={
                'ordering': ['book_title', 'book_song_index', 'storage_key'],
            },
        ),
    ]
