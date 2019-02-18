from django.apps import AppConfig as DefaultAppConfig


class AppConfig(DefaultAppConfig):
    name = "pg_partitioning"

    def ready(self):
        from .patch import schema  # noqa
