from django.apps import apps
from django.db import models, transaction
from pg_partitioning.signals import post_attach_partition, post_create_partition, post_detach_partition

from .constants import (
    SQL_APPEND_TABLESPACE,
    SQL_ATTACH_TIME_RANGE_PARTITION,
    SQL_CREATE_TIME_RANGE_PARTITION,
    SQL_DETACH_PARTITION,
    SQL_SET_TABLE_TABLESPACE,
    PeriodType,
)
from .shortcuts import double_quote, drop_table, execute_sql, generate_set_indexes_tablespace_sql, single_quote


class PartitionConfig(models.Model):
    """You can get the configuration object of the partition table through ``Model.partitioning.config``,
    You can only edit the following fields via the object's ``save`` method:
    """

    model_label = models.TextField(unique=True)
    period = models.TextField(default=PeriodType.Month)
    """Partition period. you can only set options in the `PeriodType`.
    The default value is ``PeriodType.Month``. Changing this value will trigger the ``detach_partition`` method."""
    interval = models.PositiveIntegerField(null=True)
    """Detaching period. The ``detach_partition`` method defaults to detach partitions before the interval * period.
    The default is None, ie no partition will be detached. Changing this value will trigger the ``detach_partition`` method."""
    attach_tablespace = models.TextField(null=True)
    """The name of the tablespace specified when creating or attaching a partition. Modifying this field will only affect subsequent operations.
    A table migration may occur at this time."""
    detach_tablespace = models.TextField(null=True)
    """The name of the tablespace specified when detaching a partition. Modifying this field will only affect subsequent operations.
    A table migration may occur at this time."""

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """This setting will take effect immediately when you modify the value of
        ``interval`` in the configuration.
        """

        adding = self._state.adding
        model = apps.get_model(self.model_label)

        if not adding:
            prev = self.__class__.objects.get(pk=self.pk)

        with transaction.atomic():
            super().save(force_insert, force_update, using, update_fields)
            if adding:
                # Creating first partition.
                model.partitioning.create_partition(0)

        if not adding:
            # Period or interval changed.
            if prev.period != self.period or (prev.interval != self.interval):
                model.partitioning.detach_partition()


class PartitionLog(models.Model):
    """You can only edit the following fields via the object's ``save`` method:"""

    config = models.ForeignKey(PartitionConfig, on_delete=models.CASCADE, related_name="logs")
    table_name = models.TextField(unique=True)
    # range bound: [start, end)
    start = models.DateTimeField()
    end = models.DateTimeField()
    is_attached = models.BooleanField(default=True)
    """Whether the partition is a attached partition. changing the value will trigger an attaching or detaching operation."""
    detach_time = models.DateTimeField(null=True)
    """When the value is not `None`, the partition will not be automatically detached before this time. The default is `None`."""

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """This setting will take effect immediately when you modify the value of
        ``is_attached`` in the configuration.
        """

        model = apps.get_model(self.config.model_label)
        if self._state.adding:
            sql_sequence = [
                SQL_CREATE_TIME_RANGE_PARTITION
                % {
                    "parent": double_quote(model._meta.db_table),
                    "child": double_quote(self.table_name),
                    "date_start": single_quote(self.start.isoformat()),
                    "date_end": single_quote(self.end.isoformat()),
                }
            ]

            if self.config.attach_tablespace:
                sql_sequence[0] += SQL_APPEND_TABLESPACE % {"tablespace": self.config.attach_tablespace}
                sql_sequence.extend(generate_set_indexes_tablespace_sql(self.table_name, self.config.attach_tablespace))

            with transaction.atomic():
                super().save(force_insert, force_update, using, update_fields)
                execute_sql(sql_sequence)
                post_create_partition.send(sender=model, partition_log=self)
        else:
            with transaction.atomic():
                prev = self.__class__.objects.select_for_update().get(pk=self.pk)
                # Detach partition.
                if prev.is_attached and (not self.is_attached):
                    sql_sequence = [SQL_DETACH_PARTITION % {"parent": double_quote(model._meta.db_table), "child": double_quote(self.table_name)}]
                    if self.config.detach_tablespace:
                        sql_sequence.append(SQL_SET_TABLE_TABLESPACE % {"name": double_quote(self.table_name), "tablespace": self.config.detach_tablespace})
                        sql_sequence.extend(generate_set_indexes_tablespace_sql(self.table_name, self.config.detach_tablespace))

                    super().save(force_insert, force_update, using, update_fields)
                    execute_sql(sql_sequence)
                    post_detach_partition.send(sender=model, partition_log=self)
                # Attach partition.
                elif (not prev.is_attached) and self.is_attached:
                    sql_sequence = list()
                    if self.config.attach_tablespace:
                        sql_sequence.append(SQL_SET_TABLE_TABLESPACE % {"name": double_quote(self.table_name), "tablespace": self.config.attach_tablespace})
                        sql_sequence.extend(generate_set_indexes_tablespace_sql(self.table_name, self.config.attach_tablespace))

                    sql_sequence.append(
                        SQL_ATTACH_TIME_RANGE_PARTITION
                        % {
                            "parent": double_quote(model._meta.db_table),
                            "child": double_quote(self.table_name),
                            "date_start": single_quote(self.start.isoformat()),
                            "date_end": single_quote(self.end.isoformat()),
                        }
                    )

                    super().save(force_insert, force_update, using, update_fields)
                    execute_sql(sql_sequence)
                    post_attach_partition.send(sender=model, partition_log=self)
                # State has not changed.
                else:
                    super().save(force_insert, force_update, using, update_fields)

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        """When the instance is deleted, the partition corresponding to it will also be deleted."""

        drop_table(self.table_name)
        super().delete(using, keep_parents)

    class Meta:
        ordering = ("-id",)
