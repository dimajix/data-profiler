"""The keys of a table: the columns whose values identify its rows, verified on the whole table.

A key is of one column or of two, and minimal: no column of a key of two is a key alone. A column
takes part where the table has rows, the column no nulls and no sentinels, and a type whose values
identify a row, as the dialect says - exact values, not those of floating point or of time, which
are unique by chance. As a table may have hundreds of columns, the candidates are indicated before
any of them is verified: a column of one is one whose approximate distinct count, as the statistics
counted it, reaches the rows less `_ERRORS` times the standard error the dialect counts it with, and
whose values are unique in the sample. A pair is one of two columns of values twice in the sample,
so that the sample shows what the pair tells apart, whose values together are unique in the sample,
and whose distinct counts multiplied reach the rows; of those, the `_PAIRS` whose product lies
closest to the rows, where natural keys lie - an order and its positions -, the first in the table
of several. Each candidate is verified by queries built from the building blocks of the dialect,
which count the rows and the distinct values of each candidate exactly, `_PER_QUERY` candidates at
most in one, as each count holds the values of the table in memory: a candidate is a key where they
are as many as the rows.

The primary key is the key of the fewest columns, then of whole numbers or UUIDs, as a database
generates keys, then the first in the table. The keys name columns alone, and no values of the
database.
"""

import logging
from collections.abc import Iterable, Sequence
from dataclasses import replace
from itertools import combinations
from typing import Final

from data_profiler.profile import Column, PrimaryKey, Table
from data_profiler.source import Source
from data_profiler.values import counted
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)

# How many times the standard error the dialect counts distinct values with the approximate
# distinct count of a key may lie below the rows.
_ERRORS: Final = 4
# The pairs verified at most, and the candidates verified in one query at most.
_PAIRS: Final = 10
_PER_QUERY: Final = 10


def identify(source: Source, table: Table, sample: Sample) -> Table:
    """`table` with its keys of one and two columns, verified on the whole table, and its primary.

    Args:
        source: The schema the table is in.
        table: The table, its rows counted and its columns with their statistics.
        sample: The sample of the table, with the values of each of its columns.

    Returns:
        The table with its keys, the fewer columns first, then by the places of their columns, and
        its primary key; none of either where no candidate is unique, with no query where there is
        no candidate.

    Raises:
        SourceError: The database fails to count the values of the candidates.
    """
    dialect = source.dialect
    taking = [
        column
        for column in table.columns
        if table.rows
        and column.statistics.nulls == 0
        and not column.statistics.sentinels
        and dialect.identifies(column.type)
    ]
    unique = {column.name: _unique(sample.columns[column.name]) for column in taking}
    spread = _ERRORS * dialect.distinct_error()
    singles = [
        (column.name,)
        for column in taking
        if column.statistics.distinct >= (1 - spread) * table.rows and unique[column.name]
    ]
    # A column unique in the sample takes part in no pair: it shows nothing a pair tells apart.
    paired = [column for column in taking if not unique[column.name]]
    keys = _verified(source, table, singles + _pairs(table, paired, sample))
    places = {column.name: place for place, column in enumerate(table.columns)}
    keys.sort(key=lambda key: (len(key), [places[name] for name in key]))
    # The fewest columns, then of the types a database generates keys of, then the first.
    primary = min(
        keys,
        key=lambda key: (
            len(key),
            not all(dialect.is_surrogate(table.column(name).type) for name in key),
        ),
        default=None,
    )
    _logger.info(
        "Identified the keys of %s: %d, the primary %s",
        table.name,
        len(keys),
        "none" if primary is None else ", ".join(primary),
    )
    return replace(
        table,
        keys=tuple(keys),
        primary_key=None if primary is None else PrimaryKey(columns=primary),
    )


def _pairs(table: Table, paired: Sequence[Column], sample: Sample) -> list[tuple[str, ...]]:
    """Of the pairs of `paired`, the `_PAIRS` unique in `sample` whose distinct counts are closest.

    Only pairs whose distinct counts multiplied reach the rows of `table` are tried on the sample,
    those whose product is the smallest first, the first in the table of several.
    """
    reaching = sorted(
        (
            (first, second)
            for first, second in combinations(paired, 2)
            if first.statistics.distinct * second.statistics.distinct >= table.rows
        ),
        key=lambda pair: pair[0].statistics.distinct * pair[1].statistics.distinct,
    )
    found: list[tuple[str, ...]] = []
    for first, second in reaching:
        values = zip(sample.columns[first.name], sample.columns[second.name], strict=True)
        if _unique(values):
            found.append((first.name, second.name))
            if len(found) == _PAIRS:
                break
    return found


def _verified(
    source: Source, table: Table, candidates: Sequence[tuple[str, ...]]
) -> list[tuple[str, ...]]:
    """Those of `candidates` whose values are unique in the whole table, in their order."""
    dialect = source.dialect
    step = f"verifying the keys of {source.name(table.name)}"
    verified = []
    for start in range(0, len(candidates), _PER_QUERY):
        batch = candidates[start : start + _PER_QUERY]
        expressions = [dialect.rows(), *map(dialect.exactly_distinct, batch)]
        (row,) = source.query(dialect.select(expressions, table.name), step)
        rows, *distinct = (counted(found, table.name) for found in row)
        verified += [key for key, found in zip(batch, distinct, strict=True) if found == rows]
    return verified


def _unique(values: Iterable[object]) -> bool:
    """Whether no two of `values` are equal."""
    listed = list(values)
    return len(set(listed)) == len(listed)
