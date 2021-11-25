import datetime
from unittest.mock import patch

from dateutil.relativedelta import MO, relativedelta
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import get_random_string

from pg_partitioning.constants import SQL_GET_TABLE_INDEXES, PeriodType
from pg_partitioning.models import PartitionConfig, PartitionLog
from pg_partitioning.shortcuts import single_quote

from .models import ListTableBool, ListTableInt, ListTableText, TimeRangeTableA, TimeRangeTableB


def t(year=2018, month=8, day=25, hour=7, minute=15, second=15, millisecond=0):
    """A point in time."""
    return timezone.get_current_timezone().localize(datetime.datetime(year, month, day, hour, minute, second, millisecond))


def tz(time):
    return timezone.localtime(time)


class GeneralTestCase(TestCase):
    def assertTablespace(self, table_name, tablespace):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT tablespace FROM pg_tables WHERE tablename = {single_quote(table_name)};")
            rows = cursor.fetchall()
            self.assertEqual(tablespace, rows[0][0])
            cursor.execute(SQL_GET_TABLE_INDEXES % {"table_name": single_quote(table_name)})
            rows = cursor.fetchall()
            for row in rows:
                cursor.execute(f"SELECT tablespace FROM pg_indexes WHERE indexname = {single_quote(row[0])};")
                rows = cursor.fetchall()
                self.assertEqual(tablespace, rows[0][0])


class TimeRangePartitioningTestCase(GeneralTestCase):
    def assertTimeRangeEqual(self, model, time_start, time_end):
        self.assertListEqual([time_start, time_end], [tz(model.partitioning.latest.start), tz(model.partitioning.latest.end)])

        # Verify that the partition has been created by inserting data.
        model.objects.create(text=get_random_string(length=32), timestamp=time_start)
        model.objects.create(text=get_random_string(length=32), timestamp=time_end - relativedelta(microseconds=1))

    def _create_partition(self, period, start_date, delta):
        TimeRangeTableB.partitioning.options["default_period"] = period

        for i in range(0, 3):
            if i == 0:
                TimeRangeTableB.partitioning.config  # Create first partition by side effect.
            else:
                TimeRangeTableB.partitioning.create_partition(0)
            end_date = start_date + delta
            self.assertTimeRangeEqual(TimeRangeTableB, start_date, end_date)
            start_date = end_date

    @patch("django.utils.timezone.now", new=t)
    def test_create_partition_week(self):
        self._create_partition(PeriodType.Week, t(2018, 8, 20, 0, 0, 0), relativedelta(days=1, weekday=MO))

    @patch("django.utils.timezone.now", new=t)
    def test_create_partition_day(self):
        self._create_partition(PeriodType.Day, t(2018, 8, 25, 0, 0, 0), relativedelta(days=1))

    @patch("django.utils.timezone.now", new=t)
    def test_create_partition_month(self):
        self._create_partition(PeriodType.Month, t(2018, 8, 1, 0, 0, 0), relativedelta(months=1))

    @patch("django.utils.timezone.now", new=t)
    def test_create_partition_year(self):
        self._create_partition(PeriodType.Year, t(2018, 1, 1, 0, 0, 0), relativedelta(years=1))

    @classmethod
    def _update_config_period(cls, config: PartitionConfig, period: str):
        config.period = period
        config.save()

    def test_create_partition(self):
        with patch("django.utils.timezone.now", new=t):
            config_a: PartitionConfig = TimeRangeTableA.partitioning.config

            self.assertEqual(1, config_a.logs.count())
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 8, 1, 0, 0, 0), t(2018, 9, 1, 0, 0, 0))

            # Repeated calls will not produce wrong results (idempotence).
            for _ in range(3):
                TimeRangeTableA.partitioning.create_partition()

            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 8, 1, 0, 0, 0), t(2018, 9, 1, 0, 0, 0))

            # Perform a series of partition creation operations.
            self._update_config_period(config_a, PeriodType.Week)
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 1, 0, 0, 0), t(2018, 9, 3, 0, 0, 0))

            self._update_config_period(config_a, PeriodType.Day)
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 3, 0, 0, 0), t(2018, 9, 4, 0, 0, 0))

            self._update_config_period(config_a, PeriodType.Month)
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 4, 0, 0, 0), t(2018, 10, 1, 0, 0, 0))
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 10, 1, 0, 0, 0), t(2018, 11, 1, 0, 0, 0))

            self._update_config_period(config_a, PeriodType.Year)
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 11, 1, 0, 0, 0), t(2019, 1, 1, 0, 0, 0))
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2019, 1, 1, 0, 0, 0), t(2020, 1, 1, 0, 0, 0))

    def test_max_days_to_next_partition(self):
        with patch("django.utils.timezone.now", new=t):
            TimeRangeTableA.partitioning.create_partition()
            TimeRangeTableA.partitioning.create_partition(0)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 1, 0, 0, 0), t(2018, 10, 1, 0, 0, 0))

        with patch("django.utils.timezone.now", return_value=t(2018, 8, 2, 0, 0, 0)):
            TimeRangeTableA.partitioning.create_partition(59)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 9, 1, 0, 0, 0), t(2018, 10, 1, 0, 0, 0))
            TimeRangeTableA.partitioning.create_partition(60)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 10, 1, 0, 0, 0), t(2018, 11, 1, 0, 0, 0))

        with patch("django.utils.timezone.now", return_value=t(2019, 3, 3, 0, 0, 0)):
            TimeRangeTableA.partitioning.create_partition(5)
            self.assertTimeRangeEqual(TimeRangeTableA, t(2019, 3, 1, 0, 0, 0), t(2019, 4, 1, 0, 0, 0))

    def test_attach_or_detach_partition(self):
        self.test_create_partition()

        config_a: PartitionConfig = TimeRangeTableA.partitioning.config

        self.assertEqual(0, config_a.logs.filter(is_attached=False).count())
        TimeRangeTableA.partitioning.detach_partition(config_a.logs.all())
        self.assertEqual(0, config_a.logs.filter(is_attached=True).count())
        TimeRangeTableA.partitioning.attach_partition(config_a.logs.all())
        self.assertEqual(0, config_a.logs.filter(is_attached=False).count())

        with patch("django.utils.timezone.now", return_value=t(2018, 10, 15, 12, 1, 4)):
            config_a.period = PeriodType.Day
            config_a.interval = 15
            config_a.save()
            self.assertEqual(t(2018, 10, 1, 0, 0, 0), tz(config_a.logs.filter(is_attached=True).order_by("start").first().end))
            TimeRangeTableA.partitioning.attach_partition(config_a.logs.all())

            config_a.period = PeriodType.Week
            config_a.interval = 2
            config_a.save()
            self.assertEqual(t(2018, 11, 1, 0, 0, 0), tz(config_a.logs.filter(is_attached=True).order_by("start").first().end))
            TimeRangeTableA.partitioning.attach_partition(config_a.logs.all())

            log = config_a.logs.filter(is_attached=True).order_by("start").first()
            self.assertEqual(t(2018, 9, 1, 0, 0, 0), log.end)

            log.detach_time = t(2018, 10, 15, 12, 1, 5)
            log.save()

            config_a.period = PeriodType.Month
            config_a.interval = 1
            config_a.save()

            self.assertEqual(t(2018, 9, 1, 0, 0, 0), tz(config_a.logs.filter(is_attached=True).order_by("start").first().end))
            log.refresh_from_db()
            self.assertEqual(True, log.is_attached)

            log.detach_time = None
            log.save()

            TimeRangeTableA.partitioning.detach_partition()
            self.assertEqual(t(2018, 10, 1, 0, 0, 0), tz(config_a.logs.filter(is_attached=True).order_by("start").first().end))
            log.refresh_from_db()
            self.assertEqual(False, log.is_attached)

    def test_delete_partition(self):
        for _ in range(4):
            TimeRangeTableA.partitioning.create_partition(0)

        config_a: PartitionConfig = TimeRangeTableA.partitioning.config

        TimeRangeTableA.partitioning.delete_partition(config_a.logs.all())
        self.assertEqual(0, config_a.logs.count())

        with patch("django.utils.timezone.now", new=t):
            self._update_config_period(config_a, PeriodType.Day)
            TimeRangeTableA.partitioning.create_partition()

            self.assertEqual(2, config_a.logs.count())
            self.assertTimeRangeEqual(TimeRangeTableA, t(2018, 8, 26, 0, 0, 0), t(2018, 8, 27, 0, 0, 0))

    def test_attach_detach_tablespace(self):
        TimeRangeTableA.partitioning.create_partition()
        log: PartitionLog = TimeRangeTableA.partitioning.latest
        self.assertEqual(True, log.is_attached)
        self.assertTablespace(log.table_name, log.config.attach_tablespace)

        TimeRangeTableA.partitioning.detach_partition([log])
        log.refresh_from_db()
        self.assertEqual(False, log.is_attached)
        self.assertTablespace(log.table_name, log.config.detach_tablespace)

        TimeRangeTableA.partitioning.attach_partition()
        log.refresh_from_db()
        self.assertEqual(True, log.is_attached)
        self.assertTablespace(log.table_name, log.config.attach_tablespace)


class ListPartitioningTestCase(GeneralTestCase):
    @classmethod
    def assertCreated(cls, model, category):
        # Verify that the partition has been created by inserting data.
        model.objects.create(category=category)

    def test_create_partition(self):
        ListTableText.partitioning.create_partition("list_table_text_a", "A", "data1")
        self.assertCreated(ListTableText, "A")

        ListTableText.partitioning.create_partition("list_table_text_b", "B")
        self.assertCreated(ListTableText, "B")

        ListTableText.partitioning.create_partition("list_table_text_blank", "")
        self.assertCreated(ListTableText, "")

        ListTableText.partitioning.create_partition("list_table_text_none", None, "data2")
        self.assertCreated(ListTableText, None)

        ListTableInt.partitioning.create_partition("list_table_int_1", 1, "data1")
        self.assertCreated(ListTableInt, 1)

        ListTableInt.partitioning.create_partition("list_table_int_2", 2)
        self.assertCreated(ListTableInt, 2)

        ListTableInt.partitioning.create_partition("list_table_int_none", None, "data2")
        self.assertCreated(ListTableInt, None)

        ListTableBool.partitioning.create_partition("list_table_bool_true", True, "data1")
        self.assertCreated(ListTableBool, True)

        ListTableBool.partitioning.create_partition("list_table_bool_false", False)
        self.assertCreated(ListTableBool, False)

        ListTableBool.partitioning.create_partition("list_table_bool_none", None, "data2")
        self.assertCreated(ListTableBool, None)

    def assertTablespace(self, table_name, tablespace):
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT tablespace FROM pg_tables WHERE tablename = '{table_name}';")
            rows = cursor.fetchall()
            self.assertEqual(tablespace, rows[0][0])

    def test_attach_or_detach_partition(self):
        self.test_create_partition()
        ListTableText.partitioning.detach_partition("list_table_text_none", "data1")
        self.assertTablespace("list_table_text_none", "data1")
        ListTableText.partitioning.attach_partition("list_table_text_none", None, "data2")
        self.assertTablespace("list_table_text_none", "data2")
