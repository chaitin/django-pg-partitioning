from django.contrib.postgres.indexes import BrinIndex
from django.db import models
from django.utils import timezone
from pg_timepart.constants import PeriodType
from pg_timepart.manager import TimeRangePartitioningSupport


@TimeRangePartitioningSupport(
    partition_key="timestamp", default_period=PeriodType.Month, default_attach_tablespace="data1", default_detach_tablespace="data2"
)
class ExampleModel1(models.Model):
    text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_tablespace = "pg_default"
        indexes = [BrinIndex(fields=["timestamp"])]
        unique_together = ("text", "timestamp")
        ordering = ["text"]


@TimeRangePartitioningSupport(partition_key="timestamp", default_period=PeriodType.Day, default_attach_tablespace="data2", default_detach_tablespace="data1")
class ExampleModel2(models.Model):
    text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [BrinIndex(fields=["timestamp"])]
        unique_together = ("text", "timestamp")
        ordering = ["text"]
