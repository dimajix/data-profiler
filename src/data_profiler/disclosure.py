"""Disclosure: what of the values of a table the profile may hold.

The profile holds no values of the columns found sensitive. A column keeps its range and the values
of its enumeration where it is of no sensitivity, and loses both where it is of one: by the mark
given by hand where there is one, else by its matches - where one is of a sensitive semantic type.
Sensitivity is judged optimistically: a column without a mark or such a match is of none. Each
value a column keeps is checked on its own all the same, by the types of the tool and of the
project, and withheld where it is of a sensitive type - a phone number at the end of the range of
a column of which few values are phone numbers, an IBAN of a column whose sample held none -, and a
long one is cut to its first characters, ending in `…`, so that the end of the range of a column of
free texts does not fill the profile. A table disclosed again is disclosed as before, or loses
more: what a mark of none would give back, it cannot. The sentinels of a column are no values of
it, and stay whatever its sensitivity: those of the tool are fixed texts, and those given are of the
overrides of the project, which are shared as the profile is.
"""

from collections.abc import Sequence
from dataclasses import replace
from typing import Final

from data_profiler.detect import SemanticType, is_sensitive
from data_profiler.profile import Column, Range, Table, Value

# The most characters of a value the profile holds; a value of more is cut, and its last one is `…`.
_LONGEST: Final = 100


def disclose(table: Table, types: Sequence[SemanticType]) -> Table:
    """`table` as the profile may hold it: the values of its columns of no sensitivity, none else.

    Args:
        table: The table, its columns with their statistics, matches, marks and values.
        types: The semantic types of the project, by which each value is checked beside those of
            the tool.

    Returns:
        The table, each column of no sensitivity with what it keeps of its range and values, each
        column of a sensitivity without either.
    """
    return replace(table, columns=tuple(_disclosed(column, types) for column in table.columns))


def _disclosed(column: Column, types: Sequence[SemanticType]) -> Column:
    """`column` with what it may keep of its range and values: nothing where it is sensitive."""
    statistics = column.statistics
    if column.sensitive:
        return replace(column, statistics=replace(statistics, range=None), values=())
    found = statistics.range
    shown = (
        None
        if found is None
        else Range(_shown(found.smallest, types), _shown(found.largest, types))
    )
    values = ((_shown(value.value, types), value.rows) for value in column.values)
    return replace(
        column,
        statistics=replace(statistics, range=None if shown == Range(None, None) else shown),
        values=tuple(Value(text, rows) for text, rows in values if text is not None),
    )


def _shown(text: str | None, types: Sequence[SemanticType]) -> str | None:
    """`text` as the profile holds it: None where it is of a sensitive type, cut where long."""
    if text is None or is_sensitive(text, types):
        return None
    return text if len(text) <= _LONGEST else text[: _LONGEST - 1] + "…"
