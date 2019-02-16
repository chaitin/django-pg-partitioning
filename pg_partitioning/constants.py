SQL_CREATE_TIME_RANGE_PARTITION = """\
CREATE TABLE IF NOT EXISTS %(child)s PARTITION OF %(parent)s FOR VALUES FROM (%(date_start)s) TO (%(date_end)s)"""
SQL_CREATE_LIST_PARTITION = """\
CREATE TABLE IF NOT EXISTS %(child)s PARTITION OF %(parent)s FOR VALUES IN (%(value)s)"""
SQL_SET_TABLE_TABLESPACE = """\
ALTER TABLE IF EXISTS %(name)s SET TABLESPACE %(tablespace)s"""
SQL_APPEND_TABLESPACE = " TABLESPACE %(tablespace)s"
SQL_ATTACH_TIME_RANGE_PARTITION = """\
ALTER TABLE IF EXISTS %(parent)s ATTACH PARTITION %(child)s FOR VALUES FROM (%(date_start)s) TO (%(date_end)s)"""
SQL_ATTACH_LIST_PARTITION = """\
ALTER TABLE IF EXISTS %(parent)s ATTACH PARTITION %(child)s FOR VALUES IN (%(value)s)"""
SQL_DETACH_PARTITION = "ALTER TABLE IF EXISTS %(parent)s DETACH PARTITION %(child)s"
SQL_DROP_TABLE = "DROP TABLE IF EXISTS %(name)s"
SQL_TRUNCATE_TABLE = "TRUNCATE TABLE %(name)s"
SQL_DROP_INDEX = "DROP INDEX IF EXISTS %(name)s"
SQL_CREATE_INDEX = "CREATE INDEX IF NOT EXISTS %(name)s ON %(table_name)s USING %(method)s (%(column_name)s)"
SQL_SET_INDEX_TABLESPACE = "ALTER INDEX %(name)s SET TABLESPACE %(tablespace)s"
SQL_GET_TABLE_INDEXES = "SELECT indexname FROM pg_indexes WHERE tablename = %(table_name)s"

DT_FORMAT = "%Y-%m-%d"


class PartitioningType:
    Range = "RANGE"
    List = "LIST"


class PeriodType:
    Day = "Day"
    Week = "Week"
    Month = "Month"
    Year = "Year"
