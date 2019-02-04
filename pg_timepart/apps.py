from django.apps import AppConfig as DefaultAppConfig


class AppConfig(DefaultAppConfig):
    name = "pg_timepart"

    def ready(self):
        from .patch import schema  # noqa
