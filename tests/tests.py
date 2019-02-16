import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string
from pg_partitioning.constants import PeriodType
from pg_partitioning.models import PartitionConfig

from .models import ListTable, TimeRangeTableA, TimeRangeTableB


def t(year=2018, month=8, day=25, hour=7, minute=15, second=15, millisecond=0):
    """A point in time."""
    return timezone.get_current_timezone().localize(datetime.datetime(year, month, day, hour, minute, second, millisecond))


def tz(time):
    return timezone.localtime(time)


class TimeRangePartitioningTestCase(TestCase):
    def assertTimeRangeEqual(self, obj, time_start, time_end):
        self.assertListEqual([time_start, time_end], [tz(obj.partitioning.latest.start), tz(obj.partitioning.latest.end)])
        obj.objects.create(text=get_random_string(length=32), timestamp=time_start)
        obj.objects.create(text=get_random_string(length=32), timestamp=time_end - relativedelta(microseconds=1))

    def test_create_partition(self):
        with patch("django.utils.timezone.now", new=t):
            # Idempotency.
            for _ in range(3):
                TimeRangeTableA.partitioning.create_partition()
                TimeRangeTableB.partitioning.create_partition()
            self.assertEqual(1, TimeRangeTableA.partitioning.config.logs.count())
            self.assertEqual(2, TimeRangeTableB.partitioning.config.logs.count())
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 8, 1, 0, 0, 0), t(2018, 9, 1, 0, 0, 0))
            self.assertTimeRangeEqual(TimeRangeTableB, t(2018, 8, 26, 0, 0, 0), t(2018, 8, 27, 0, 0, 0))
            # Week
            PartitionConfig.objects.filter(model_label=TimeRangeTableA._meta.label_lower).update(period=PeriodType.Week)
            PartitionConfig.objects.filter(model_label=TimeRangeTableB._meta.label_lower).update(period=PeriodType.Week)
            TimeRangeTableB.partitioning.create_partition(0)  # Forced creation of new partitions.
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableB, t(2018, 8, 27, 0, 0, 0), t(2018, 9, 3, 0, 0, 0))
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 3, 0, 0, 0), t(2018, 9, 10, 0, 0, 0))
            # Day
            PartitionConfig.objects.filter(model_label=TimeRangeTableA._meta.label_lower).update(period=PeriodType.Day)
            PartitionConfig.objects.filter(model_label=TimeRangeTableB._meta.label_lower).update(period=PeriodType.Day)
            TimeRangeTableA.partitioning.create_partition(0)
            TimeRangeTableB.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 10, 0, 0, 0), t(2018, 9, 11, 0, 0, 0))
            TimeRangeTableB.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableB, t(2018, 9, 4, 0, 0, 0), t(2018, 9, 5, 0, 0, 0))
            # Month
            PartitionConfig.objects.filter(model_label=TimeRangeTableA._meta.label_lower).update(period=PeriodType.Month)
            PartitionConfig.objects.filter(model_label=TimeRangeTableB._meta.label_lower).update(period=PeriodType.Month)
            TimeRangeTableA.partitioning.create_partition(0)
            TimeRangeTableB.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableB, t(2018, 9, 5, 0, 0, 0), t(2018, 10, 1, 0, 0, 0))
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 10, 1, 0, 0, 0), t(2018, 11, 1, 0, 0, 0))
            # Year
            PartitionConfig.objects.filter(model_label=TimeRangeTableA._meta.label_lower).update(period=PeriodType.Year)
            PartitionConfig.objects.filter(model_label=TimeRangeTableB._meta.label_lower).update(period=PeriodType.Year)
            TimeRangeTableA.partitioning.create_partition(0)
            TimeRangeTableB.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 11, 1, 0, 0, 0), t(2019, 1, 1, 0, 0, 0))
            TimeRangeTableB.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableB, t(2019, 1, 1, 0, 0, 0), t(2020, 1, 1, 0, 0, 0))
        # set max_days_to_next_partition
        with patch("django.utils.timezone.now", return_value=t(2018, 6, 1, 0, 0, 0)):
            TimeRangeTableA.partitioning.create_partition()
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 11, 1, 0, 0, 0), t(2019, 1, 1, 0, 0, 0))
            TimeRangeTableA.partitioning.create_partition(215)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2019, 1, 1, 0, 0, 0), t(2020, 1, 1, 0, 0, 0))

    def test_attach_or_detach_partition(self):
        self.test_create_partition()
        self.assertEqual(0, TimeRangeTableA.partitioning.config.logs.filter(is_attached=False).count())
        TimeRangeTableA.partitioning.detach_partition(TimeRangeTableA.partitioning.config.logs.all())
        self.assertEqual(0, TimeRangeTableA.partitioning.config.logs.filter(is_attached=True).count())
        TimeRangeTableA.partitioning.attach_partition(TimeRangeTableA.partitioning.config.logs.all())
        self.assertEqual(0, TimeRangeTableA.partitioning.config.logs.filter(is_attached=False).count())

        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config = TimeRangeTableA.partitioning.config
            config.period = PeriodType.Day
            config.interval = 15
            config.save()
            self.assertEqual(t(2018, 10, 1, 0, 0, 0), tz(TimeRangeTableA.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
        TimeRangeTableA.partitioning.attach_partition(TimeRangeTableA.partitioning.config.logs.all())

        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config = TimeRangeTableA.partitioning.config
            config.period = PeriodType.Week
            config.interval = 2
            config.save()
            self.assertEqual(t(2018, 11, 1, 0, 0, 0), tz(TimeRangeTableA.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
        TimeRangeTableA.partitioning.attach_partition(TimeRangeTableA.partitioning.config.logs.all())

        log = TimeRangeTableA.partitioning.config.logs.filter(is_attached=True).order_by("start").first()
        log.detach_time = t(2018, 10, 15, 12, 1, 5)
        log.save()
        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config = TimeRangeTableA.partitioning.config
            config.period = PeriodType.Month
            config.interval = 1
            config.save()
            self.assertEqual(t(2018, 9, 1, 0, 0, 0), tz(TimeRangeTableA.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
            log.refresh_from_db()
            self.assertEqual(True, log.is_attached)
        log.detach_time = None
        log.save()
        TimeRangeTableA.partitioning.detach_partition()
        self.assertEqual(t(2020, 1, 1, 0, 0, 0), tz(TimeRangeTableA.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
        log.refresh_from_db()
        self.assertEqual(False, log.is_attached)
        TimeRangeTableA.partitioning.attach_partition(TimeRangeTableA.partitioning.config.logs.all())

    def test_delete_partition(self):
        self.test_create_partition()
        TimeRangeTableB.partitioning.delete_partition(TimeRangeTableB.partitioning.config.logs.all())


class ListPartitioningTestCase(TestCase):
    @classmethod
    def test_create_partition(cls):
        ListTable.partitioning.create_partition("list_table_a", "A", "data1")
        ListTable.partitioning.create_partition("list_table_b", "B")
        ListTable.partitioning.create_partition("list_table_blank", "")
        ListTable.partitioning.create_partition("list_table_none", None, "data2")

    def test_attach_or_detach_partition(self):
        self.test_create_partition()
        ListTable.partitioning.detach_partition("list_table_none", "data1")
        ListTable.partitioning.attach_partition("list_table_none", None)
