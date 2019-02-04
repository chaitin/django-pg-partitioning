import logging
from typing import List, Optional, Tuple, Union

from django.db import connection

logger = logging.getLogger(__name__)


def single_quote(name: str) -> str:
    if name.startswith("'") and name.endswith("'"):
        return name
    return "'%s'" % name


def double_quote(name: str) -> str:
    if name.startswith('"') and name.endswith('"'):
        return name
    return '"%s"' % name


def execute_sql(sql_sequence: Union[str, List[str], Tuple[str]], fetch: bool = False) -> Optional[Tuple]:
    sql_str = ""
    for statement in sql_sequence if isinstance(sql_sequence, (list, tuple)) else [sql_sequence]:
        sql_str += ";\n" + statement if sql_str else statement
    logger.debug("The sequence of SQL statements to be executed:\n %s", sql_str)
    with connection.cursor() as cursor:
        cursor.execute(sql_str)
        if fetch:
            return cursor.fetchall()
