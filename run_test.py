import argparse
import sys

import dj_database_url
import django
from django.core.management import call_command


def setup_django_environment():
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            "default": dj_database_url.config(env="DATABASE_URL",
                                              default="postgres://test:test@localhost/test",
                                              conn_max_age=20)
        },
        SECRET_KEY="not very secret in tests",
        USE_I18N=True,
        USE_L10N=True,
        USE_TZ=True,
        TIME_ZONE="Asia/Shanghai",
        INSTALLED_APPS=(
            "pg_partitioning",
            "tests",
        ),
        LOGGING={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "[%(asctime)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "standard"
                }
            },
            "loggers": {
                "pg_partitioning.utils": {
                    "handlers": ["console"],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "pg_partitioning.patch.schema": {
                    "handlers": ["console"],
                    "level": "DEBUG",
                    "propagate": False,
                },
            },
        }
    )

    django.setup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the pg_partitioning test suite.")
    parser.add_argument("-c", "--coverage", dest="use_coverage", action="store_true", help="Run coverage to collect code coverage and generate report.")
    options = parser.parse_args()

    if options.use_coverage:
        try:
            from coverage import coverage
        except ImportError:
            options.use_coverage = False

    if options.use_coverage:
        cov = coverage()
        cov.start()

    setup_django_environment()
    call_command("test", verbosity=2, interactive=False, stdout=sys.stdout)

    if options.use_coverage:
        print("\nRunning Code Coverage...\n")
        cov.stop()
        cov.report()
        cov.xml_report()
