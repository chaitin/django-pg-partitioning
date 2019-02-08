Decorators
==========

Now the decorator must be used on a non-abstract model class that has not yet built a table in the database.
If you must use the decorator on a model class that has previously performed a migrate operation, you need
to back up the model's data, then drop the table, and then import the data after you have created a
partitioned table.

.. py:currentmodule:: pg_timepart.manager

.. autodata:: TimeRangePartitioningSupport
   :annotation:

Post-Decoration
---------------

You can run ``makemigrations`` and ``migrate`` commands to create and apply new migrations.
Once the table has been created, it is not possible to turn a regular table into a partitioned table or vice versa.
