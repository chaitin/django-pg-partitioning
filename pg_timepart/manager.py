import datetime
from collections import Iterable
from typing import Optional

import pytz
from dateutil.relativedelta import MO, relativedelta
from django.conf import settings
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils import timezone

from .constants import DT_FORMAT, PeriodType
from .models import PartitionConfig, PartitionLog


class TimeRangePartitioning:
    """Class of partitioned model attribute ``partitioning``. Provide some common methods for managing partitions.
    """

    def __init__(self, model, partition_key, options):
        self.model = model
        self.partition_key = partition_key
        self.options = options

    @property
    def config(self) -> PartitionConfig:
        """Get the latest PartitionConfig instance of this model.
        In order to avoid the race condition, we used ``select_for_update`` when querying.

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

    def truncate_all_partition(self) -> None:
        """Clear all data from partitioned table.
        """
        for log in self.config.logs.all():
            log.truncate()


class TimeRangePartitioningSupport:
    """Use this decorator to declare the database table corresponding to the model to be partitioned by time range.

    Parameters:
      partition_key(str): Partition field name of DateTimeField.
      options: Currently supports the following keyword parameters:

        - default_period(PeriodType): Default partition period.
        - default_interval(int): Default detach partition interval.
        - default_attach_tablespace(str): Default tablespace for attached tables.
        - default_detach_tablespace(str): Default tablespace for attached tables.

    Example:
      .. code-block:: python

          from django.db import models
          from django.utils import timezone

          from pg_timepart.manager import TimeRangePartitioningSupport


          @TimeRangePartitioningSupport(partition_key="timestamp")
          class MyLog(models.Model):
              name = models.TextField(default="Hello World!")
              timestamp = models.DateTimeField(default=timezone.now, primary_key=True)
    """

    def __init__(self, partition_key: str, **options):
        self.partition_key = partition_key
        self.options = options

    def __call__(self, model):

        if not issubclass(model, models.Model):
            raise ValueError("Invalid decorated class.")

        if model._meta.get_field(self.partition_key).get_internal_type() != models.DateTimeField().get_internal_type():
            raise ValueError("The partition_key must be DateTimeField type.")

        model.partitioning = TimeRangePartitioning(model, self.partition_key, self.options)

        return model
