import datetime
from collections import Iterable
from typing import Optional, Type, Union

import pytz
from dateutil.relativedelta import MO, relativedelta
from django.conf import settings
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils import timezone
from pg_partitioning.shortcuts import double_quote, execute_sql, generate_set_indexes_tablespace_sql, single_quote

from .constants import (
    DT_FORMAT,
    SQL_APPEND_TABLESPACE,
    SQL_ATTACH_LIST_PARTITION,
    SQL_CREATE_LIST_PARTITION,
    SQL_DETACH_PARTITION,
    SQL_SET_TABLE_TABLESPACE,
    PartitioningType,
    PeriodType,
)
from .models import PartitionConfig, PartitionLog


class _PartitionManagerBase:
    type = None

    def __init__(self, model: Type[models.Model], partition_key: str, options: dict):
        self.model = model
        self.partition_key = partition_key
        self.options = options


class TimeRangePartitionManager(_PartitionManagerBase):
    """Manage time-based partition APIs."""

    type = PartitioningType.Range

    @property
    def config(self) -> PartitionConfig:
        """Get the latest PartitionConfig instance of this model.
        In order to avoid the race condition, we used **select_for_update** when querying.

        Returns:
          PartitionConfig: The latest PartitionConfig instance of this model.
        """
        try:
            return PartitionConfig.objects.select_for_update().get(model_label=self.model._meta.label_lower)
        except PartitionConfig.DoesNotExist:
            try:
                return PartitionConfig.objects.create(
                    model_label=self.model._meta.label_lower,
                    period=self.options.get("default_period", PeriodType.Month),
                    interval=self.options.get("default_interval"),
                    attach_tablespace=self.options.get("default_attach_tablespace"),
                    detach_tablespace=self.options.get("default_detach_tablespace"),
                )
            except IntegrityError:
                return PartitionConfig.objects.select_for_update().get(model_label=self.model._meta.label_lower)

    @property
    def latest(self) -> Optional[PartitionLog]:
        """Get the latest PartitionLog instance of this model.

        Returns:
          Optional[PartitionLog]: The latest PartitionLog instance of this model or none.
        """
        return self.config.logs.order_by("-id").first()

    @classmethod
    def _get_period_bound(cls, date_start, initial, addition_zeros=None, is_week=False, **kwargs):
        zeros = {"hour": 0, "minute": 0, "second": 0, "microsecond": 0}
        if addition_zeros:
            zeros.update(addition_zeros)

        def func():  # lazy evaluation
            if initial:
                start = date_start.replace(**zeros)
                if is_week:
                    start -= relativedelta(days=start.weekday())
            else:
                start = date_start
            end = start + relativedelta(**kwargs, **zeros)
            return start, end

        return func

    def create_partition(self, max_days_to_next_partition: int = 1) -> None:
        """The partition of the next cycle is created according to the configuration.
        After modifying the period field, the new period will take effect the next time.
        The start time of the new partition is the end time of the previous partition table,
        or the start time of the current archive period when no partition exists.

        For example:
        the current time is June 5, 2018, and the archiving period is one year,
        then the start time of the first partition is 00:00:00 on January 1, 2018.

        Parameters:
          max_days_to_next_partition(int):
            If numbers of days remained in current partition is greater than ``max_days_to_next_partition``, no new partitions will be created.
        """
        while True:
            if max_days_to_next_partition > 0 and self.latest and timezone.now() < (self.latest.end - relativedelta(days=max_days_to_next_partition)):
                return

            partition_timezone = getattr(settings, "PARTITION_TIMEZONE", None)
            if partition_timezone:
                partition_timezone = pytz.timezone(partition_timezone)
            date_start = timezone.localtime(self.latest.end if self.latest else None, timezone=partition_timezone)
            initial = not bool(self.latest)
            date_start, date_end = {
                PeriodType.Day: self._get_period_bound(date_start, initial, days=+1),
                PeriodType.Week: self._get_period_bound(date_start, initial, is_week=True, days=+1, weekday=MO),
                PeriodType.Month: self._get_period_bound(date_start, initial, addition_zeros=dict(day=1), months=+1),
                PeriodType.Year: self._get_period_bound(date_start, initial, addition_zeros=dict(month=1, day=1), years=+1),
            }[self.config.period]()

            partition_table_name = "_".join((self.model._meta.db_table, date_start.strftime(DT_FORMAT), date_end.strftime(DT_FORMAT)))
            PartitionLog.objects.create(config=self.config, table_name=partition_table_name, start=date_start, end=date_end)

            if not max_days_to_next_partition > 0:
                return

    def attach_partition(self, partition_log: Optional[Iterable] = None, detach_time: Optional[datetime.datetime] = None) -> None:
        """Attach partitions.

        Parameters:
          partition_log(Optional[Iterable]):
            All partitions are attached when you don't specify partitions to attach.
          detach_time(Optional[datetime.datetime]):
            When the partition specifies the archive time, it will **not** be automatically archived until that time.
        """
        if not partition_log:
            partition_log = PartitionLog.objects.filter(config=self.config, is_attached=False)

        for log in partition_log:
            log.is_attached = True
            log.detach_time = detach_time
            log.save()

    def detach_partition(self, partition_log: Optional[Iterable] = None) -> None:
        """Detach partitions.

        Parameters:
          partition_log(Optional[Iterable]):
            Specify a partition to archive. When you don't specify a partition to archive, all partitions that meet the configuration rule are archived.
        """
        if not partition_log:
            if self.config.interval:
                # fmt: off
                period = {PeriodType.Day: {"days": 1},
                          PeriodType.Week: {"weeks": 1},
                          PeriodType.Month: {"months": 1},
                          PeriodType.Year: {"years": 1}}[self.config.period]
                # fmt: on
                now = timezone.now()
                detach_timeline = now - self.config.interval * relativedelta(**period)
                partition_log = PartitionLog.objects.filter(config=self.config, end__lt=detach_timeline, is_attached=True)
                partition_log = partition_log.filter(Q(detach_time=None) | Q(detach_time__lt=now))
            else:
                return

        for log in partition_log:
            log.is_attached = False
            log.detach_time = None
            log.save()

    def delete_partition(self, partition_log: Iterable) -> None:
        """Delete partitions.

        Parameters:
          partition_log(Iterable): The partitions to be deleted.
        """
        for log in partition_log:
            if log.config == self.config:
                log.delete()


def _db_value(value: Union[str, int, bool, None]) -> str:
    if value is None:
        return "null"
    return single_quote(value) if isinstance(value, str) else str(value)


class ListPartitionManager(_PartitionManagerBase):
    """Manage list-based partition APIs."""

    type = PartitioningType.List

    def create_partition(self, partition_name: str, value: Union[str, int, bool, None], tablespace: str = None) -> None:
        """Create partitions.

        Parameters:
          partition_name(str): Partition name.
          value(Union[str, int, bool, None]): Partition key value.
          tablespace(str): Partition tablespace name.
        """

        sql_sequence = [
            SQL_CREATE_LIST_PARTITION % {"parent": double_quote(self.model._meta.db_table), "child": double_quote(partition_name), "value": _db_value(value)}
        ]
        if tablespace:
            sql_sequence[0] += SQL_APPEND_TABLESPACE % {"tablespace": tablespace}
            sql_sequence.extend(generate_set_indexes_tablespace_sql(partition_name, tablespace))
        execute_sql(sql_sequence)

    def attach_partition(self, partition_name: str, value: Union[str, int, bool, None], tablespace: str = None) -> None:
        """Attach partitions.

        Parameters:
          partition_name(str): Partition name.
          value(Union[str, int, bool, None]): Partition key value.
          tablespace(str): Partition tablespace name.
        """

        sql_sequence = list()
        if tablespace:
            sql_sequence.append(SQL_SET_TABLE_TABLESPACE % {"name": double_quote(partition_name), "tablespace": tablespace})
            sql_sequence.extend(generate_set_indexes_tablespace_sql(partition_name, tablespace))
        sql_sequence.append(
            SQL_ATTACH_LIST_PARTITION
            % {"parent": double_quote(self.model._meta.db_table), "child": double_quote(partition_name), "value": single_quote(_db_value(value))}
        )
        execute_sql(sql_sequence)

    def detach_partition(self, partition_name: str, tablespace: str = None) -> None:
        """Detach partitions.

        Parameters:
          partition_name(str): Partition name.
          tablespace(str): Partition tablespace name.
        """
        sql_sequence = [SQL_DETACH_PARTITION % {"parent": double_quote(self.model._meta.db_table), "child": double_quote(partition_name)}]
        if tablespace:
            sql_sequence.append(SQL_SET_TABLE_TABLESPACE % {"name": double_quote(partition_name), "tablespace": tablespace})
            sql_sequence.extend(generate_set_indexes_tablespace_sql(partition_name, tablespace))
        execute_sql(sql_sequence)
