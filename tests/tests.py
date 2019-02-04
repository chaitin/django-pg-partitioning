import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string

from .models import ExampleModel1, ExampleModel2
from pg_timepart.constants import PeriodType
from pg_timepart.models import PartitionConfig
from pg_timepart.utils import double_quote, execute_sql, single_quote


def t(year=2018, month=8, day=25, hour=7, minute=15, second=15, millisecond=0):
    """A point in time."""
    return timezone.get_current_timezone().localize(datetime.datetime(year, month, day, hour, minute, second, millisecond))


def tz(time):
    return timezone.localtime(time)


class PartitioningTestCase(TestCase):
    def generate_data(self, model, time_start, time_end, num=100):
        interval = (time_end - time_start) / num
        for i in range(num):
            model.objects.create(text=get_random_string(length=32), timestamp=time_start + interval * i)

    def assertTimeRangeEqual(self, obj, time_start, time_end):
        self.assertListEqual([time_start, time_end], [tz(obj.partitioning.latest.start), tz(obj.partitioning.latest.end)])
        self.generate_data(obj, time_start, time_end)

    def test_create_partition(self):
        with patch("django.utils.timezone.now", new=t):
            for _ in range(3):
                ExampleModel1.partitioning.create_partition()
                ExampleModel2.partitioning.create_partition()
            self.assertEqual(ExampleModel1.partitioning.config.logs.count(), 1)
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 8, 1, 0, 0, 0), t(2018, 9, 1, 0, 0, 0))
            # Week
            PartitionConfig.objects.filter(model_label=ExampleModel1._meta.label_lower).update(period=PeriodType.Week)
            PartitionConfig.objects.filter(model_label=ExampleModel2._meta.label_lower).update(period=PeriodType.Week)
            ExampleModel2.partitioning.create_partition(0)
            ExampleModel1.partitioning.create_partition(0)
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 9, 1, 0, 0, 0), t(2018, 9, 3, 0, 0, 0))
            ExampleModel1.partitioning.create_partition(0)
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 9, 3, 0, 0, 0), t(2018, 9, 10, 0, 0, 0))
            # Day
            PartitionConfig.objects.filter(model_label=ExampleModel1._meta.label_lower).update(period=PeriodType.Day)
            PartitionConfig.objects.filter(model_label=ExampleModel2._meta.label_lower).update(period=PeriodType.Day)
            ExampleModel1.partitioning.create_partition(0)
            ExampleModel2.partitioning.create_partition(0)
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 9, 10, 0, 0, 0), t(2018, 9, 11, 0, 0, 0))
            # Month
            PartitionConfig.objects.filter(model_label=ExampleModel1._meta.label_lower).update(period=PeriodType.Month)
            PartitionConfig.objects.filter(model_label=ExampleModel2._meta.label_lower).update(period=PeriodType.Month)
            ExampleModel1.partitioning.create_partition(0)
            ExampleModel2.partitioning.create_partition(0)
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 9, 11, 0, 0, 0), t(2018, 10, 1, 0, 0, 0))
            # Year
            PartitionConfig.objects.filter(model_label=ExampleModel1._meta.label_lower).update(period=PeriodType.Year)
            PartitionConfig.objects.filter(model_label=ExampleModel2._meta.label_lower).update(period=PeriodType.Year)
            ExampleModel1.partitioning.create_partition(0)
            ExampleModel2.partitioning.create_partition(0)
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 10, 1, 0, 0, 0), t(2019, 1, 1, 0, 0, 0))
        # set max_days_to_next_partition
        with patch("django.utils.timezone.now", return_value=t(2018, 6, 1, 0, 0, 0)):
            ExampleModel1.partitioning.create_partition()
            self.assertTimeRangeEqual(ExampleModel1, t(2018, 10, 1, 0, 0, 0), t(2019, 1, 1, 0, 0, 0))
            ExampleModel1.partitioning.create_partition(216)
            self.assertTimeRangeEqual(ExampleModel1, t(2019, 1, 1, 0, 0, 0), t(2020, 1, 1, 0, 0, 0))

    def test_attach_and_detach_partition(self):
        self.test_create_partition()
        self.assertEqual(0, ExampleModel1.partitioning.config.logs.filter(is_attached=False).count())
        log_num = ExampleModel1.partitioning.config.logs.count()
        ExampleModel1.partitioning.detach_partition(ExampleModel1.partitioning.config.logs.all())
        self.assertEqual(log_num, ExampleModel1.partitioning.config.logs.filter(is_attached=False).count())
        ExampleModel1.partitioning.attach_partition(ExampleModel1.partitioning.config.logs.all())
        self.assertEqual(log_num, ExampleModel1.partitioning.config.logs.filter(is_attached=True).count())

        log = ExampleModel1.partitioning.latest
        log.is_attached = False
        log.save()
        self.assertEqual(False, ExampleModel1.partitioning.latest.is_attached)
        log.is_attached = True
        log.save()
        self.assertEqual(True, ExampleModel1.partitioning.latest.is_attached)

        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config = ExampleModel1.partitioning.config
            config.period = PeriodType.Day
            config.interval = 15
            config.save()
            self.assertEqual(t(2018, 10, 1, 0, 0, 0), tz(ExampleModel1.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
        ExampleModel1.partitioning.attach_partition(ExampleModel1.partitioning.config.logs.all())

        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config = ExampleModel1.partitioning.config
            config.period = PeriodType.Week
            config.interval = 2
            config.save()
            self.assertEqual(t(2019, 1, 1, 0, 0, 0), tz(ExampleModel1.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
        ExampleModel1.partitioning.attach_partition(ExampleModel1.partitioning.config.logs.all())

        log = ExampleModel1.partitioning.config.logs.filter(is_attached=True).order_by("start").first()
        log.detach_time = t(2018, 10, 15, 12, 1, 5)
        log.save()
        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config = ExampleModel1.partitioning.config
            config.period = PeriodType.Month
            config.interval = 1
            config.save()
            self.assertEqual(t(2018, 9, 1, 0, 0, 0), tz(ExampleModel1.partitioning.config.logs.filter(is_attached=True).order_by("start").first().end))
        log.detach_time = None
        log.save()
        ExampleModel1.partitioning.attach_partition(ExampleModel1.partitioning.config.logs.all())

    def test_truncate_partition(self):
        self.test_create_partition()
        ExampleModel2.partitioning.truncate_all_partition()
        self.assertEqual(0, ExampleModel2.objects.count())

    def test_delete_partition(self):
        self.test_create_partition()
        ExampleModel2.partitioning.delete_partition(ExampleModel2.partitioning.config.logs.all())

    def test_set_tablespace(self):
        self.test_create_partition()
        ExampleModel2.partitioning.latest.set_tablespace("data1")
        ExampleModel2.partitioning.latest.set_tablespace("data2")


class UtilsTestCase(TestCase):
    def test_utils(self):
        _ = execute_sql("SELECT EXTRACT(EPOCH FROM INTERVAL '5 days 3 hours');", fetch=True)[0]  # noqa
        name = "'name'"
        self.assertEqual(name, single_quote(name))
        name = '"name"'
        self.assertEqual(name, double_quote(name))
