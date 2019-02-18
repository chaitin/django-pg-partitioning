API Reference
=============

.. py:currentmodule:: pg_partitioning.manager

Time Range Partitioning
-----------------------

.. autoclass:: TimeRangePartitionManager
   :members:

.. autoclass:: PartitionConfig
   :members: period, interval, attach_tablespace, detach_tablespace, save

.. autoclass:: PartitionLog
   :members: is_attached, detach_time, save, delete

List Partitioning
-----------------

.. autoclass:: ListPartitionManager
   :members:

.. py:currentmodule:: pg_partitioning.shortcuts

Shortcuts
---------

.. automodule:: pg_partitioning.shortcuts
   :members: truncate_table, set_tablespace, drop_table
