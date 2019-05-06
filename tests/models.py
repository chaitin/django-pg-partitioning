from django.contrib.postgres.indexes import BrinIndex
from django.db import models
from django.utils import timezone
from pg_partitioning.constants import PeriodType
from pg_partitioning.decorators import ListPartitioning, TimeRangePartitioning


@TimeRangePartitioning(partition_key="timestamp", default_period=PeriodType.Month, default_attach_tablespace="data1", default_detach_tablespace="data2")
class TimeRangeTableA(models.Model):
    text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_tablespace = "pg_default"
        indexes = [BrinIndex(fields=["timestamp"])]
        unique_together = ("text", "timestamp")
        ordering = ["text"]


@TimeRangePartitioning(partition_key="timestamp", default_period=PeriodType.Day, default_attach_tablespace="data2", default_detach_tablespace="data1")
class TimeRangeTableB(models.Model):
    text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [BrinIndex(fields=["timestamp"])]
        unique_together = ("text", "timestamp")
        ordering = ["text"]


@ListPartitioning(partition_key="category")
class ListTableText(models.Model):
    category = models.TextField(default="A", null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)


@ListPartitioning(partition_key="category")
class ListTableInt(models.Model):
    category = models.IntegerField(default=0, null=True)
    timestamp = models.DateTimeField(default=timezone.now)


@ListPartitioning(partition_key="category")
class ListTableBool(models.Model):
    category = models.NullBooleanField(default=False, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
