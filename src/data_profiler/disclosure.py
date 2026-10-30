"""Disclosure: what of the values of a table goes into the profile.

The profile holds no values of the columns found sensitive. The range of a column and the values
of its enumeration go into it where the column is of no sensitivity - where none of its matches is
of a sensitive semantic type -, and are taken out of it where it is of one. Sensitivity is judged
optimistically: a column without such a match is of none. Each value that goes into the profile is
checked on its own all the same, and withheld where it is of a sensitive type - a phone number at
the end of the range of a column of which few values are phone numbers, an IBAN of a column whose
sample held none. Each value is written as text, as the database writes it.
"""

from collections.abc import Sequence
from dataclasses import replace

from data_profiler.detect import Sensitivity, is_sensitive
from data_profiler.profile import Column, Range, Table, Value
from data_profiler.source import as_text
from data_profiler.workspace import Enumeration


def disclose(table: Table, enumerations: Sequence[Enumeration]) -> Table:
    """`table` as the profile may hold it: the values of its columns of no sensitivity, none else.

    Args:
        table: The table, its columns with their statistics and matches.
        enumerations: The enumerations of the table, as the workspace holds them.

    Returns:
        The table, each column of no sensitivity with its range and the values of its
        enumeration, each column of a sensitivity without either.
    """
    values = {enumeration.column: enumeration.values for enumeration in enumerations}
    return replace(
        table,
        columns=tuple(_disclosed(column, values.get(column.name, ())) for column in table.columns),
    )


def _disclosed(column: Column, values: Sequence[tuple[object, int]]) -> Column:
    """`column` with its range and `values`, or without either where it is of a sensitivity.

    Of a column of no sensitivity, a value that is of a sensitive type is withheld all the same.
    """
    statistics = column.statistics
    if column.sensitivity is not Sensitivity.NONE:
        return replace(column, statistics=replace(statistics, range=None), values=())
    found = statistics.range
    shown = None if found is None else Range(_shown(found.smallest), _shown(found.largest))
    texts = ((as_text(value), rows) for value, rows in values)
    return replace(
        column,
        statistics=replace(statistics, range=None if shown == Range(None, None) else shown),
        values=tuple(Value(text, rows) for text, rows in texts if not is_sensitive(text)),
    )


def _shown(text: str | None) -> str | None:
    """`text`, or None where it is of a sensitive type."""
    return None if text is None or is_sensitive(text) else text
