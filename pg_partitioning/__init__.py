"""
A Django extension that supports PostgreSQL 11 time ranges and list partitioning.
"""
REQUIRED_DJANGO_VERSION = [(2, 0), (3, 0)]
DJANGO_VERSION_ERROR = "django-pg-partitioning isn't available on the currently installed version of Django."

try:
    import django
except ImportError:
    raise ImportError(DJANGO_VERSION_ERROR)

if REQUIRED_DJANGO_VERSION[0] > tuple(django.VERSION[:2]) or tuple(django.VERSION[:2]) > REQUIRED_DJANGO_VERSION[1]:
    raise ImportError(DJANGO_VERSION_ERROR)


__version__ = "0.12"

default_app_config = "pg_partitioning.apps.AppConfig"
