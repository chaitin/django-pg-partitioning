import logging
from typing import Type

from django.db import models

from pg_partitioning.manager import ListPartitionManager, TimeRangePartitionManager

logger = logging.getLogger(__name__)


class _PartitioningBase:
    def __init__(self, partition_key: str, **options):
        self.partition_key = partition_key
        self.options = options

    def __call__(self, model: Type[models.Model]):
        if model._meta.abstract:
            raise NotImplementedError("Decorative abstract model classes are not supported.")


class TimeRangePartitioning(_PartitioningBase):
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

          from pg_partitioning.decorators import TimeRangePartitioning


          @TimeRangePartitioning(partition_key="timestamp")
          class MyLog(models.Model):
              name = models.TextField(default="Hello World!")
              timestamp = models.DateTimeField(default=timezone.now, primary_key=True)
    """

    def __call__(self, model: Type[models.Model]):
        super().__call__(model)
        if model._meta.get_field(self.partition_key).get_internal_type() != models.DateTimeField().get_internal_type():
            raise ValueError("The partition_key must be DateTimeField type.")
        model.partitioning = TimeRangePartitionManager(model, self.partition_key, self.options)
        return model


class ListPartitioning(_PartitioningBase):
    """Use this decorator to declare the database table corresponding to the model to be partitioned by list.

    Parameters:
      partition_key(str): Partition key name, the type of the key must be one of boolean, text or integer.
      check_partition_key_type(bool): Check Partition field validity, for example if you want partitioning by ForeignKey.

    Example:
      .. code-block:: python

          from django.db import models
          from django.utils import timezone

          from pg_partitioning.decorators import ListPartitioning


          @ListPartitioning(partition_key="category")
          class MyLog(models.Model):
              category = models.TextField(default="A")
              timestamp = models.DateTimeField(default=timezone.now, primary_key=True)
    """

    def __init__(self, partition_key: str, check_partition_key_type: bool = True, **options):
        super().__init__(partition_key, **options)
        self.check_partition_key_type = check_partition_key_type

    def __call__(self, model: Type[models.Model]):
        super().__call__(model)
        if self.check_partition_key_type:
            support_field_types = [item.get_internal_type() for item in [models.TextField(), models.BooleanField(), models.IntegerField()]]
            if model._meta.get_field(self.partition_key).get_internal_type() not in support_field_types:
                raise NotImplementedError("The partition_key does not support this field type.")
        model.partitioning = ListPartitionManager(model, self.partition_key, self.options)
        return model
