django-pg-partitioning
======================
.. image:: https://img.shields.io/badge/License-MIT-orange.svg?style=flat-square
   :target: https://raw.githubusercontent.com/chaitin/django-pg-partitioning/master/LICENSE
.. image:: https://img.shields.io/badge/Django-2.0_2.1-green.svg?style=flat-square&logo=django
   :target: https://www.djangoproject.com/
.. image:: https://img.shields.io/badge/PostgreSQL-11-lightgrey.svg?style=flat-square&logo=postgresql
   :target: https://www.postgresql.org/
.. image:: https://readthedocs.org/projects/django-pg-partitioning/badge/?version=latest&style=flat-square
   :target: https://django-pg-partitioning.readthedocs.io
.. image:: https://img.shields.io/pypi/v/django-pg-partitioning.svg?style=flat-square
   :target: https://pypi.org/project/django-pg-partitioning/
.. image:: https://api.travis-ci.org/chaitin/django-pg-partitioning.svg?branch=master
   :target: https://travis-ci.org/chaitin/django-pg-partitioning
.. image:: https://api.codacy.com/project/badge/Grade/c872699c1b254e90b540b053343d1e81
   :target: https://www.codacy.com/app/xingji2163/django-pg-partitioning?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=chaitin/django-pg-partitioning&amp;utm_campaign=Badge_Grade
.. image:: https://codecov.io/gh/chaitin/django-pg-partitioning/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/chaitin/django-pg-partitioning

一个支持 PostgreSQL 11 原生表分区的 Django 扩展，使您可以在 Django 中创建分区表并管理它们。目前它支持两种分区类型：

- 时间范围分区（Time Range Partitioning）：将时序数据分开存储到不同的时间范围分区表中，支持创建连续且不重叠的时间范围分区并进行归档管理。
- 列表分区（List Partitioning）：根据分区字段的确定值将数据分开存储到不同的分区表中。

----

A Django extension that supports PostgreSQL 11 native table partitioning, allowing you to create partitioned tables in Django
and manage them. Currently it supports the following two partition types:

- **Time Range Partitioning**: Separate time series data into different time range partition tables,
  support the creation of continuous and non-overlapping time range partitions and archival management.
- **List Partitioning**: Store data separately into different partition tables based on the determined values of the partition key.

Documentation
  https://django-pg-partitioning.readthedocs.io

.. image:: https://raw.githubusercontent.com/chaitin/django-pg-partitioning/master/docs/source/_static/carbon.png
   :align: center

TODO
----
- Improve the details of the function.
- Improve documentation and testing.
- Optimization implementation.

maybe more...

Contributing
------------
If you want to contribute to a project and make it better, you help is very welcome!
Please read through `Contributing Guidelines <https://github.com/chaitin/django-pg-partitioning/blob/master/CONTRIBUTING.rst>`__.

License
-------
This project is licensed under the MIT. Please see `LICENSE <https://raw.githubusercontent.com/chaitin/django-pg-partitioning/master/LICENSE>`_.

Project Practice
----------------
.. image:: https://raw.githubusercontent.com/chaitin/django-pg-timepart/master/docs/source/_static/safeline.svg?sanitize=true
   :target: https://www.chaitin.cn/en/safeline
