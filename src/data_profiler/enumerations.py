"""The enumerations of a table, counted by one query built from the building blocks of the dialect.

A column is an enumeration if the statistics counted at most `_LIMIT` distinct values in it, and
not each of them in one row alone: the values of a key of a small table say nothing about what it
is. A column of more values is never grouped by: grouped by a column of keys, a table of hundreds
of millions of rows would fill the memory of the database with a group for each. Nor is a column
whose values no closed list holds, however few they are, as the next load brings a new one: one of
a type the dialect takes for none - UUIDs, times, floating numbers -, or of a match of a semantic
type that is none - UUIDs and dates written as text -, so that the matches of the table are
recognised first. A column of lists is none either, as its texts are lists; the values of its lists
may be, counted by the module `lists` on a source of a row of each. The query groups
the table by each of the columns on its own, in one pass, and counts the rows of each value; null
is no value of an enumeration, as the statistics count the nulls, and nor is a sentinel, which the
statistics count each. The values are values of the database, as the text the dialect reads them
as; they go into the workspace, never into the log, and into the profile only as the module
`disclosure` lets them.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Final

from data_profiler.counts import counted
from data_profiler.profile import Column, Table, Value
from data_profiler.source import Dialect, Source
from data_profiler.workspace import Enumeration

_logger = logging.getLogger(__name__)

# The most distinct values a column of an enumeration has.
_LIMIT: Final = 500


def values(source: Source, table: Table) -> list[Enumeration]:
    """The enumerations of `table` of `source`, with the rows of each of their values.

    Args:
        source: The schema the table is in.
        table: The table, with its columns, their statistics and matches, and its columns of lists
            with their separators.

    Returns:
        The enumerations, in the order of the columns of the table.

    Raises:
        SourceError: The database fails to count the values.
    """
    dialect = source.dialect
    asked = {c.name: c for c in table.columns if _may_be_one(dialect, c)}
    kinds = {name: column.type for name, column in asked.items()}
    by_column = _count(source, table.name, kinds) if asked else {}
    enumerations = []
    for name, found in by_column.items():
        column = asked[name]
        kept = [
            (value, rows)
            for value, rows in found
            if dialect.is_filled(column.type, value, column.left_aside)
        ]
        if any(rows > 1 for _, rows in kept):
            ordered = tuple(sorted(kept, key=lambda v: v[1], reverse=True))
            enumerations.append(Enumeration(column=name, values=ordered))
    _logger.info(
        "Counted the values of %s: %d enumerations", source.name(table.name), len(enumerations)
    )
    return enumerations


def _may_be_one(dialect: Dialect, column: Column) -> bool:
    """Whether `column` may be an enumeration: of few values, no lists, and a type that may be."""
    return (
        0 < column.statistics.distinct <= _LIMIT
        and column.list_separator is None
        and dialect.is_enumerable(column.type)
        and all(match.type.enumerable for match in column.matches)
    )


def _count(
    source: Source, table: str, columns: Mapping[str, str]
) -> dict[str, list[tuple[object, int]]]:
    """The values of each of `columns`, by their types, of `table` but null, with their rows."""
    step = f"counting the values of {source.name(table)}"
    by_column: dict[str, list[tuple[object, int]]] = {name: [] for name in columns}
    for name, value, (rows,) in source.grouped(table, columns, [source.dialect.rows()], step):
        if value is not None:
            by_column[name].append((value, counted(rows, f"{table}.{name}")))
    return by_column


def valued(table: Table, enumerations: Sequence[Enumeration]) -> Table:
    """`table`, each column of an enumeration with its values, as text, the most frequent first.

    Args:
        table: The table, with its columns.
        enumerations: The enumerations of its columns, as `values` counted them.

    Returns:
        The table, each column of one of `enumerations` with its values, every other as it is.
    """
    found = {enumeration.column: enumeration.values for enumeration in enumerations}
    columns = (
        replace(
            column,
            values=tuple(Value(str(value), rows) for value, rows in found[column.name]),
        )
        if column.name in found
        else column
        for column in table.columns
    )
    return replace(table, columns=tuple(columns))
