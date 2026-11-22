from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authorization', '0006_recentlyopenedsong'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='playlist',
            name='members',
            field=models.ManyToManyField(
                blank=True,
                related_name='shared_playlists',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
