"""Disclosure: what of the values of a table the profile may hold.

The profile holds no values of the columns found sensitive. A column keeps its range and the values
of its enumeration where it is of no sensitivity, and loses both where it is of one: by the mark
given by hand where there is one, else by its matches - where one is of a sensitive semantic type.
Sensitivity is judged optimistically: a column without a mark or such a match is of none. Each
value a column keeps is checked on its own all the same, and withheld where it is of a sensitive
type - a phone number at the end of the range of a column of which few values are phone numbers,
an IBAN of a column whose sample held none -, and a long one is cut to its first characters, ending
in `…`, so that the end of the range of a column of free texts does not fill the profile. A table
disclosed again is disclosed as before, or loses more: what a mark of none would give back, it
cannot.
"""

from dataclasses import replace
from typing import Final

from data_profiler.detect import Sensitivity, is_sensitive
from data_profiler.profile import Column, Range, Table, Value

# The most characters of a value the profile holds; a value of more is cut, and its last one is `…`.
_LONGEST: Final = 100


def disclose(table: Table) -> Table:
    """`table` as the profile may hold it: the values of its columns of no sensitivity, none else.

    Args:
        table: The table, its columns with their statistics, matches, marks and values.

    Returns:
        The table, each column of no sensitivity with what it keeps of its range and values, each
        column of a sensitivity without either.
    """
    return replace(table, columns=tuple(_disclosed(column) for column in table.columns))


def _disclosed(column: Column) -> Column:
    """`column` with what it may keep of its range and values: nothing where it is sensitive."""
    statistics = column.statistics
    if column.sensitivity is not Sensitivity.NONE:
        return replace(column, statistics=replace(statistics, range=None), values=())
    found = statistics.range
    shown = None if found is None else Range(_shown(found.smallest), _shown(found.largest))
    values = ((_shown(value.value), value.rows) for value in column.values)
    return replace(
        column,
        statistics=replace(statistics, range=None if shown == Range(None, None) else shown),
        values=tuple(Value(text, rows) for text, rows in values if text is not None),
    )


def _shown(text: str | None) -> str | None:
    """`text` as the profile holds it: None where it is of a sensitive type, cut where long."""
    if text is None or is_sensitive(text):
        return None
    return text if len(text) <= _LONGEST else text[: _LONGEST - 1] + "…"
