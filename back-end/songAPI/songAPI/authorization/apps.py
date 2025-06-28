from django.apps import AppConfig


class SheetmusicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'songAPI.authorization'

    def ready(self):
        import songAPI.authorization.signals
