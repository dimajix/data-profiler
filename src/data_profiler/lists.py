"""Columns of lists: the columns of a table whose texts are lists of values, found in its sample.

The separator of the values of a list is configured, not guessed: the project gives one, the same in
all its tables, and an override of a table one in its place. A column of text is one of lists where
the module `detect` takes the values of the sample, its nulls and sentinels aside, for lists of
values separated by it; a column of texts of one value each is none, though each is a list of one,
and a column of no text is none, though a decimal written as text, `12.50`, would be a list of a
dot. No
query is needed. A column of lists is no candidate of a discriminator, as its texts are no values
of one.
"""

import logging
from dataclasses import replace

from data_profiler.detect import is_list
from data_profiler.profile import Table
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)


def listed(table: Table, sample: Sample, separator: str | None) -> Table:
    """`table`, each column whose sample holds lists of values separated by `separator` with it.

    Args:
        table: The table, with its columns and their statistics.
        sample: The sample of the table, with the values of each of its columns.
        separator: The separator of the values of a list, or None where none is given, so that no
            column is one of lists.

    Returns:
        The table, each column of text of lists with its separator, every other without one.
    """
    columns = tuple(
        replace(
            column,
            list_separator=separator
            if separator is not None
            # Only a column of text has lengths.
            and column.statistics.lengths is not None
            and is_list(sample.columns[column.name], separator, column.left_aside)
            else None,
        )
        for column in table.columns
    )
    found = [column.name for column in columns if column.list_separator is not None]
    _logger.info("Found the columns of lists of %s: %d", table.name, len(found))
    _logger.debug("The columns of lists of %s: %s", table.name, ", ".join(found))
    return replace(table, columns=columns)


def is_listed_with(table: Table, separator: str | None) -> bool:
    """Whether `table` was counted with `separator`: none of its columns a list of another.

    A table counted without a separator, or of no list, cannot be told from one counted with it.

    Args:
        table: The table, as a profile holds it.
        separator: The separator of the values of a list it is to be counted with, or None.

    Returns:
        Whether each of its columns of lists has `separator`.
    """
    return all(column.list_separator in (None, separator) for column in table.columns)
