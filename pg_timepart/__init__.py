"""
A Django extension that provides database table partition management.
"""
REQUIRED_DJANGO_VERSION = [(2, 0), (2, 1)]
DJANGO_VERSION_ERROR = "django-pg-timepart isn't available on the currently installed version of Django."

try:
    import django
except ImportError:
    raise ImportError(DJANGO_VERSION_ERROR)

if REQUIRED_DJANGO_VERSION[0] > tuple(django.VERSION[:2]) or tuple(django.VERSION[:2]) > REQUIRED_DJANGO_VERSION[1]:
    raise ImportError(DJANGO_VERSION_ERROR)


__version__ = "0.0.9"

default_app_config = "pg_timepart.apps.AppConfig"
