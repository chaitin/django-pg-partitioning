Signals
=======

There are several signals emitted during the **save** method is called.
You can hook to them for your own needs (for example to create corresponding table index).

.. py:currentmodule:: partitioning.signals

.. autodata:: post_create_partition(sender, partition_log)
  :annotation:
.. autodata:: post_attach_partition(sender, partition_log)
  :annotation:
.. autodata:: post_detach_partition(sender, partition_log)
  :annotation:
