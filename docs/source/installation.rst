Installation
============

PyPI
----

.. code-block:: bash

   $ pip install django-pg-partitioning

Or you can install from GitHub

.. code-block:: bash

   $ pip install git+https://github.com/chaitin/django-pg-partitioning.git@master

Integrate with Django
---------------------

Add ``pg_partitioning`` to ``INSTALLED_APPS`` in settings.py.

Important - Please note 'pg_partitioning' should be loaded earlier than other apps that depend on it::

    INSTALLED_APPS = [
        'pg_partitioning',
        ...
    ]

    PARTITION_TIMEZONE = "Asia/Shanghai"

You can specify the time zone referenced by the time range partitioned table via ``PARTITION_TIMEZONE``,
and if it is not specified, ``TIME_ZONE`` value is used.

Post-Installation
-----------------

In your Django root execute the command below to create 'pg_partitioning' database tables::

    ./manage.py migrate pg_partitioning

