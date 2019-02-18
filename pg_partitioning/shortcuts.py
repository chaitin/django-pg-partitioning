import logging
from typing import List, Optional, Tuple, Union

from django.db import connection
from pg_partitioning.constants import SQL_DROP_TABLE, SQL_GET_TABLE_INDEXES, SQL_SET_INDEX_TABLESPACE, SQL_SET_TABLE_TABLESPACE, SQL_TRUNCATE_TABLE

logger = logging.getLogger(__name__)


def single_quote(name: str) -> str:
    """Represent a string constants in SQL."""

    if name.startswith("'") and name.endswith("'"):
        return name
    return "'%s'" % name


def double_quote(name: str) -> str:
    """Represent a identify in SQL."""

    if name.startswith('"') and name.endswith('"'):
        return name
    return '"%s"' % name


def execute_sql(sql_sequence: Union[str, List[str], Tuple[str]], fetch: bool = False) -> Optional[Tuple]:
    """Execute SQL sequence and returning result."""

    sql_str = ""
    for statement in sql_sequence if isinstance(sql_sequence, (list, tuple)) else [sql_sequence]:
        sql_str += ";\n" + statement if sql_str else statement
    logger.debug("The sequence of SQL statements to be executed:\n %s", sql_str)
    with connection.cursor() as cursor:
        cursor.execute(sql_str)
        if fetch:
            return cursor.fetchall()


def generate_set_indexes_tablespace_sql(table_name: str, tablespace: str) -> List[str]:
    """Generate set indexes tablespace SQL sequence.

    Parameters:
      table_name(str): Table name.
      tablespace(str): Partition tablespace.
    """

    sql_sequence = []
    result = execute_sql(SQL_GET_TABLE_INDEXES % {"table_name": single_quote(table_name)}, fetch=True)
    for item in result:
        sql_sequence.append(SQL_SET_INDEX_TABLESPACE % {"name": double_quote(item[0]), "tablespace": tablespace})
    return sql_sequence


def set_tablespace(table_name: str, tablespace: str) -> None:
    """Set the tablespace for a table and indexes.

    Parameters:
      table_name(str): Table name.
      tablespace(str): Tablespace name.
    """

    sql_sequence = [SQL_SET_TABLE_TABLESPACE % {"name": double_quote(table_name), "tablespace": tablespace}]
    sql_sequence.extend(generate_set_indexes_tablespace_sql(table_name, tablespace))
    execute_sql(sql_sequence)


def truncate_table(table_name: str) -> None:
    """Truncate table.

    Parameters:
      table_name(str): Table name.
    """

    execute_sql(SQL_TRUNCATE_TABLE % {"name": double_quote(table_name)})


def drop_table(table_name: str) -> None:
    """Drop table.

    Parameters:
      table_name(str): Table name.
    """

    execute_sql(SQL_DROP_TABLE % {"name": double_quote(table_name)})
