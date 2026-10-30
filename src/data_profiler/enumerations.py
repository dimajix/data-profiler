"""The enumerations of a table, counted by one query built from the building blocks of the dialect.

A column is an enumeration if the statistics counted at most `_LIMIT` distinct values in it, and
not each of them in one row alone: the values of a key of a small table say nothing about what it
is. A column of more values is never grouped by: grouped by a column of keys, a table of hundreds
of millions of rows would fill the memory of the database with a group for each. The query groups
the table by each of the columns on its own, in one pass, and counts the rows of each value; null
is no value of an enumeration, as the statistics count the nulls. The values are values of the
database; they go into the workspace alone, never into the profile or the log.
"""

import logging
from typing import Final

from data_profiler.profile import Table
from data_profiler.source import Source, counted
from data_profiler.workspace import Enumeration

_logger = logging.getLogger(__name__)

# The most distinct values a column of an enumeration has.
_LIMIT: Final = 500


def values(source: Source, table: Table) -> list[Enumeration]:
    """The enumerations of `table` of `source`, with the rows of each of their values.

    Args:
        source: The schema the table is in.
        table: The table, with its columns and their statistics.

    Returns:
        The enumerations, in the order of the columns of the table.

    Raises:
        SourceError: The database fails to count the values.
    """
    names = [column.name for column in table.columns if 0 < column.statistics.distinct <= _LIMIT]
    by_column = _count(source, table.name, names) if names else {}
    enumerations = [
        Enumeration(column=name, values=tuple(sorted(found, key=lambda v: v[1], reverse=True)))
        for name, found in by_column.items()
        if any(rows > 1 for _, rows in found)
    ]
    _logger.info("Counted the values of %s: %d enumerations", table.name, len(enumerations))
    return enumerations


def _count(source: Source, table: str, names: list[str]) -> dict[str, list[tuple[object, int]]]:
    """The values of each of the columns `names` of `table` but null, with the rows of each."""
    dialect = source.dialect
    expressions = [
        *(dialect.column(name) for name in names),
        *(dialect.grouping(name) for name in names),
        dialect.rows(),
    ]
    statement = dialect.grouped(expressions, table, names)
    by_column: dict[str, list[tuple[object, int]]] = {name: [] for name in names}
    for row in source.query(statement, f"counting the values of {source.name(table)}"):
        # The row belongs to the one column whose grouping is 0; the others are null in it.
        groupings = row[len(names) : -1]
        if groupings.count(0) != 1:
            raise TypeError(f"the query grouped a row of {table} by other than one column")
        index = groupings.index(0)
        if row[index] is not None:
            rows = counted(row[-1], f"{table}.{names[index]}")
            by_column[names[index]].append((row[index], rows))
    return by_column
