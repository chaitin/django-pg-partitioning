from django.apps import apps
from django.db import models, transaction

from pg_timeparti.signals import post_attach_partition, post_create_partition, post_detach_partition
from .constants import (
    SQL_APPEND_TABLESPACE,
    SQL_ATTACH_PARTITION,
    SQL_CREATE_PARTITION,
    SQL_DETACH_PARTITION,
    SQL_DROP_TABLE,
    SQL_GET_TABLE_INDEXES,
    SQL_SET_INDEX_TABLESPACE,
    SQL_SET_TABLE_TABLESPACE,
    SQL_TRUNCATE_TABLE,
    PeriodType,
)
from .utils import double_quote, execute_sql, single_quote


def set_index_tablespace(table_name: str, tablespace: str):
    sqls = []
    result = execute_sql(SQL_GET_TABLE_INDEXES % {"tablename": single_quote(table_name)}, fetch=True)
    for item in result:
        sqls.append(SQL_SET_INDEX_TABLESPACE % {"name": double_quote(item[0]), "tablespace": tablespace})
    return sqls


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
    """You can only edit the following fields via the object's ``save`` method:
    """

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
            sqls = [
                SQL_CREATE_PARTITION
                % {
                    "parent": double_quote(model._meta.db_table),
                    "child": double_quote(self.table_name),
                    "date_start": single_quote(self.start.isoformat()),
                    "date_end": single_quote(self.end.isoformat()),
                }
            ]

            if self.config.attach_tablespace:
                sqls[0] += SQL_APPEND_TABLESPACE % {"tablespace": self.config.attach_tablespace}
                sqls.extend(set_index_tablespace(self.table_name, self.config.attach_tablespace))

            with transaction.atomic():
                super().save(force_insert, force_update, using, update_fields)
                execute_sql(sqls)
                post_create_partition.send(sender=model, partition_log=self)
        else:
            with transaction.atomic():
                prev = self.__class__.objects.select_for_update().get(pk=self.pk)
                # attach -> detach
                if prev.is_attached and (not self.is_attached):
                    sqls = [SQL_DETACH_PARTITION % {"parent": double_quote(model._meta.db_table), "child": double_quote(self.table_name)}]
                    if self.config.detach_tablespace:
                        sqls.append(SQL_SET_TABLE_TABLESPACE % {"name": double_quote(self.table_name), "tablespace": self.config.detach_tablespace})
                        sqls.extend(set_index_tablespace(self.table_name, self.config.detach_tablespace))

                    super().save(force_insert, force_update, using, update_fields)
                    execute_sql(sqls)
                    post_detach_partition.send(sender=model, partition_log=self)
                # detach -> attach
                elif (not prev.is_attached) and self.is_attached:
                    sqls = list()
                    if self.config.attach_tablespace:
                        sqls.append(SQL_SET_TABLE_TABLESPACE % {"name": double_quote(self.table_name), "tablespace": self.config.attach_tablespace})
                        sqls.extend(set_index_tablespace(self.table_name, self.config.attach_tablespace))

                    sqls.append(
                        SQL_ATTACH_PARTITION
                        % {
                            "parent": double_quote(model._meta.db_table),
                            "child": double_quote(self.table_name),
                            "date_start": single_quote(self.start.isoformat()),
                            "date_end": single_quote(self.end.isoformat()),
                        }
                    )

                    super().save(force_insert, force_update, using, update_fields)
                    execute_sql(sqls)
                    post_attach_partition.send(sender=model, partition_log=self)
                # Nothing changed.
                else:
                    super().save(force_insert, force_update, using, update_fields)

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        """When the instance is deleted, the partition corresponding to it will also be deleted.
        """
        execute_sql(SQL_DROP_TABLE % {"name": double_quote(self.table_name)})
        super().delete(using, keep_parents)

    def truncate(self):
        """Truncating the partition.
        """
        execute_sql(SQL_TRUNCATE_TABLE % {"name": double_quote(self.table_name)})

    def set_tablespace(self, tablespace: str):
        """Set the tablespace for this partition.
        """
        sqls = [SQL_SET_TABLE_TABLESPACE % {"name": double_quote(self.table_name), "tablespace": tablespace}]
        sqls.extend(set_index_tablespace(self.table_name, tablespace))
        execute_sql(sqls)

    class Meta:
        ordering = ("-id",)
