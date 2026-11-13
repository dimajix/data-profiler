"""Columns of lists: the columns of a table whose texts are lists of values, and their values.

The separator of the values of a list is configured, not guessed: the project gives one, the same in
all its tables, and an override of a table one in its place, or none. A column of text is one of
lists where the module `detect` takes the values of the sample, its nulls and sentinels aside, as
the dialect tells them, for lists of values separated by it; a column of texts of one value each is
none, though each is a list of one, and a column of no text is none, though a decimal written as
text, `12.50`, would be a list of a dot. No query is needed. An override of a column gives its
separator, or none, whatever is found, warned of where its sample holds no lists of it. The texts
of a column of lists are no enumeration, as the module `enumerations` says, and no values of a
discriminator; the values of its lists are, as the module `entities` says.

The values of the lists of a column are counted as the values of a column are, by the modules that
count those, of a source that reads the table as a row of each value, `Source.unnested`: their
statistics by `statistics`, their enumeration by `enumerations`, their semantic types recognised by
`matching` in the texts of the sample split at the separator, and verified on that source, with the
sentinels given of the column, else those of the tool; whether they are an enumeration, an override
of the column gives, as of a column. They are the items of the column; what of their values the
profile holds, the module `disclosure` decides, as of the column.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import replace

from data_profiler.detect import SemanticType, is_list
from data_profiler.enumerations import valued, values
from data_profiler.matching import recognise, verify
from data_profiler.overrides import GivenSeparators
from data_profiler.profile import Column, Table
from data_profiler.source import Dialect, Source
from data_profiler.statistics import count
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)


def listed(
    dialect: Dialect,
    table: Table,
    sample: Sample,
    separator: str | None,
    given: GivenSeparators,
) -> Table:
    """`table`, each column given a separator of lists, or of lists of `separator`, with it.

    Args:
        dialect: The dialect of the database, which tells the sentinels of a sample and the types
            that hold texts.
        table: The table, with its columns and their statistics.
        sample: The sample of the table, with the values of each of its columns.
        separator: The separator of the values of a list, or None where none is given, so that no
            column is one of lists but those given one.
        given: The separator of lists of each column, given by hand, or False where it is none,
            by the name of the column, of those it is given of; a column of a type that holds no
            texts is given none.

    Returns:
        The table, each column of text given none whose sample holds lists of `separator` with
        it, each column given a separator with it, whatever its sample holds, every other without
        one.
    """
    columns = tuple(
        replace(
            column,
            list_separator=_separator(dialect, table.name, column, sample, separator, given),
        )
        for column in table.columns
    )
    found = [column.name for column in columns if column.list_separator is not None]
    _logger.info("Found the columns of lists of %s: %d", table.name, len(found))
    _logger.debug("The columns of lists of %s: %s", table.name, ", ".join(found))
    return replace(table, columns=columns)


def _separator(
    dialect: Dialect,
    table: str,
    column: Column,
    sample: Sample,
    separator: str | None,
    given: GivenSeparators,
) -> str | None:
    """The separator of the lists of `column`, of `table`, as `listed` finds or is given it."""
    of_column = given.get(column.name)
    if of_column is None:
        if separator is None or not dialect.is_text(column.type):
            return None
        return separator if is_list(_filled(dialect, column, sample), separator) else None
    if of_column is False:
        return None
    if not is_list(_filled(dialect, column, sample), of_column):
        _logger.warning(
            "The overrides give %s.%s a separator of lists its sample holds no lists of",
            table,
            column.name,
        )
    return of_column


def _filled(dialect: Dialect, column: Column, sample: Sample) -> list[object]:
    """The values of `column` in `sample` but its nulls and sentinels, as `dialect` tells them."""
    return [
        value
        for value in sample.columns[column.name]
        if dialect.is_filled(column.type, value, column.left_aside)
    ]


def itemize(
    source: Source,
    table: Table,
    sample: Sample,
    types: Sequence[SemanticType],
    enumerations: Mapping[str, bool],
) -> Table:
    """`table`, each of its columns of lists with the values of its lists counted, its items.

    Args:
        source: The schema the table is in.
        table: The table, its columns of lists with their separators.
        sample: The sample of the table, with the values of each of its columns.
        types: The semantic types of the project, recognised beside those of the tool.
        enumerations: Whether the values of the lists of each column are an enumeration, given by
            hand, by the name of the column, of those it is given of.

    Returns:
        The table, each column of lists with its items, every other as it is.

    Raises:
        SourceError: The database fails to list the columns of the table, or to count, enumerate
            or verify the values of a list.
    """
    columns = tuple(
        column
        if column.list_separator is None
        else _itemized(
            source, table.name, column, column.list_separator, sample, types, enumerations
        )
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
    enumerations: Mapping[str, bool],
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
    recognised = recognise(source.dialect, counted, Sample({column.name: split}), types)
    found = verify(unnested, recognised)
    (item,) = valued(found, values(unnested, found, enumerations)).columns
    return replace(column, items=item.findings)
