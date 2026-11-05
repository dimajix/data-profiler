"""The enumerations of a table, counted by one query built from the building blocks of the dialect.

A column is an enumeration if the statistics counted at most `_LIMIT` distinct values in it, and
not each of them in one row alone: the values of a key of a small table say nothing about what it
is. A column of more values is never grouped by: grouped by a column of keys, a table of hundreds
of millions of rows would fill the memory of the database with a group for each. The query groups
the table by each of the columns on its own, in one pass, and counts the rows of each value; null
is no value of an enumeration, as the statistics count the nulls, and nor is a sentinel, which the
statistics count each. The values are values of the database; they go into the workspace, never
into the log, and into the profile only as the module `disclosure` lets them.
"""

import logging
from typing import Final

from data_profiler.detect import is_sentinel
from data_profiler.profile import Table
from data_profiler.source import Source
from data_profiler.values import counted
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
    asked = {c.name: c for c in table.columns if 0 < c.statistics.distinct <= _LIMIT}
    by_column = _count(source, table.name, list(asked)) if asked else {}
    enumerations = []
    for name, found in by_column.items():
        kept = [
            (value, rows) for value, rows in found if not is_sentinel(value, asked[name].left_aside)
        ]
        if any(rows > 1 for _, rows in kept):
            ordered = tuple(sorted(kept, key=lambda v: v[1], reverse=True))
            enumerations.append(Enumeration(column=name, values=ordered))
    _logger.info("Counted the values of %s: %d enumerations", table.name, len(enumerations))
    return enumerations


def _count(source: Source, table: str, names: list[str]) -> dict[str, list[tuple[object, int]]]:
    """The values of each of the columns `names` of `table` but null, with the rows of each."""
    step = f"counting the values of {source.name(table)}"
    by_column: dict[str, list[tuple[object, int]]] = {name: [] for name in names}
    for index, value, (rows,) in source.grouped(table, names, [source.dialect.rows()], step):
        if value is not None:
            by_column[names[index]].append((value, counted(rows, f"{table}.{names[index]}")))
    return by_column
