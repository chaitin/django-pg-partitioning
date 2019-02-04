Installation
============

GitHub
------

.. code-block:: bash

   $ pip install git+https://github.com/chaitin/django-partitioning.git@master

PyPI
----

.. code-block:: bash

   $ pip install django-pg-timepart

Django
------

settings.py (Important - Please note 'django-partitioning' is loaded earlier than the app that depends on it)::

    INSTALLED_APPS = [
        'pg_timepart',
        ...
    ]

    PARTITION_TIMEZONE = "Asia/Shanghai"

You can specify the time zone referenced by the time range partitioned table via `PARTITION_TIMEZONE`,
and if it is not specified, get the value of `TIME_ZONE`.

Post-Installation
-----------------

In your Django root execute the command below to create 'pg_timepart' database tables::

    ./manage.py migrate pg_timepart
