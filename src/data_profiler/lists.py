"""Columns of lists: the columns of a table whose texts are lists of values, and their values.

The separator of the values of a list is configured, not guessed: the project gives one, the same in
all its tables, and an override of a table one in its place. A column of text is one of lists where
the module `detect` takes the values of the sample, its nulls and sentinels aside, for lists of
values separated by it; a column of texts of one value each is none, though each is a list of one,
and a column of no text is none, though a decimal written as text, `12.50`, would be a list of a
dot. No query is needed. A column of lists is no candidate of a discriminator, as its texts are no
values of one.

The values of the lists of a column are counted as the values of a column are, by the modules that
count those, of a source that reads the table as a row of each value, `Source.unnested`: their
statistics by `statistics`, their enumeration by `enumerations`, their semantic types recognised by
`matching` in the texts of the sample split at the separator, and verified on that source, with the
sentinels given of the column, else those of the tool. They are the items of the column; what of
their values the profile holds, the module `disclosure` decides, as of the column.
"""

import logging
from collections.abc import Sequence
from dataclasses import replace

from data_profiler.detect import SemanticType, is_list
from data_profiler.enumerations import valued, values
from data_profiler.matching import recognise, verify
from data_profiler.profile import Column, Table
from data_profiler.source import Source
from data_profiler.statistics import count
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


def itemize(source: Source, table: Table, sample: Sample, types: Sequence[SemanticType]) -> Table:
    """`table`, each of its columns of lists with the values of its lists counted, its items.

    Args:
        source: The schema the table is in.
        table: The table, its columns of lists with their separators.
        sample: The sample of the table, with the values of each of its columns.
        types: The semantic types of the project, recognised beside those of the tool.

    Returns:
        The table, each column of lists with its items, every other as it is.

    Raises:
        SourceError: The database fails to list the columns of the table, or to count, enumerate
            or verify the values of a list.
    """
    columns = tuple(
        column
        if column.list_separator is None
        else _itemized(source, table.name, column, column.list_separator, sample, types)
        for column in table.columns
    )
    listed = sum(1 for column in columns if column.items is not None)
    _logger.info("Counted the values of the lists of %s: %d columns", table.name, listed)
    return replace(table, columns=columns)


def _itemized(
    source: Source,
    table: str,
    column: Column,
    separator: str,
    sample: Sample,
    types: Sequence[SemanticType],
) -> Column:
    """`column` of lists of `separator`, of `table`, with the values of its lists, its items."""
    unnested = source.unnested(table, column.name, separator)
    given = {} if column.sentinels is None else {column.name: column.sentinels}
    counted = count(unnested, table, given, columns=(column.name,))
    split = [
        value
        for text in sample.columns[column.name]
        if text is not None
        for value in str(text).strip().split(separator)
    ]
    found = verify(unnested, recognise(counted, Sample({column.name: split}), types))
    (item,) = valued(found, values(unnested, found)).columns
    return replace(column, items=item.findings)
