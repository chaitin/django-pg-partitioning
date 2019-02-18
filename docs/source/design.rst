Design
======

A brief description of the architecture of django-pg-partitioning.

Partitioned Table Support
-------------------------

Currently Django does not support creating partitioned tables, so django-partitioning monkey patch ``create_model`` method in
``DatabaseSchemaEditor`` to make it generate SQL statements that create partitioned tables.

Some of the operations that Django applies to regular database tables may not be supported or even conflicted on the partitioned
table, eventually throwing a database exception. Therefore, it is recommended that you read the section on the partition table
in the official database documentation and refer to the relevant implementation inside Django.

Constraint Limitations
----------------------

It is important to note that PostgreSQL table partitioning has some restrictions on field constraints.
In order for the extension to work, we turned off Django's automatically generated primary key constraint, but did not do other legality checks.
For example, if you mistakenly used a unique or foreign key constraint, it will throw an exception directly, which is what you are coding and
it needs to be manually circumvented during use.

Tablespace
----------

``pg_partitioning`` will silently set the tablespace of all local partitioned indexes under one partition to be consistent with
the partition.

Partition Information
---------------------

``pg_partitioning`` saves partition configuration and state information in ``PartitionConfig`` and ``PartitionLog``.
The problem with this is that once this information is inconsistent with the actual situation, ``pg_partitioning``
will not work properly, so you can only fix it manually.

Management
----------

You can use ``Model.partitioning.create_partition`` and ``Model.partitioning.detach_partition`` to automatically create and
archive partitions. In addition setting ``default_detach_tablespace`` and ``default_attach_tablespace``, you can also use the
``set_tablespace`` method of the PartitionLog object to move the partition. See :doc:`api` for details.
