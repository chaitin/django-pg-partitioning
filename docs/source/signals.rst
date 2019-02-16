Signals
=======

Note that these signals are only triggered when the save methods of ``PartitionConfig`` and ``PartitionLog``
You can hook to them for your own needs (for example to create corresponding table index).

.. py:currentmodule:: pg_partitioning.signals

.. autodata:: post_create_partition(sender, partition_log)
  :annotation:
.. autodata:: post_attach_partition(sender, partition_log)
  :annotation:
.. autodata:: post_detach_partition(sender, partition_log)
  :annotation:
