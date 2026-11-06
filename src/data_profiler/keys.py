"""The keys of a table: the columns whose values identify its rows, verified on the whole table.

A key is of one column or of two, and minimal: no column of a key of two is a key alone. A column
takes part where the table has rows, the column no nulls and no sentinels, and a type whose values
identify a row, as the dialect says - exact values, not those of floating point or of time, which
are unique by chance. As a table may have hundreds of columns, the keys are indicated before any of
them is verified: a key of one column is indicated where its approximate distinct count, as the
statistics counted it, reaches the rows less `_ERRORS` times the standard error the dialect counts
it with, and its values are unique in the sample. A pair is indicated where its two columns have
values twice in the sample, so that the sample shows what the pair tells apart, its values together
are unique in the sample, and their distinct counts multiplied reach the rows; of those, the
`_PAIRS` whose product lies closest to the rows, where natural keys lie, such as an order and its
positions, the first in the table of several. Each key indicated is verified by queries built from
the building blocks of the dialect, which count the rows and the distinct values of each exactly,
`_PER_QUERY` at most in one, as each count holds the values of the table in memory: it is a key
where they are as many as the rows.

The primary key is the one the overrides give, verified with the keys indicated: a key where it is
unique, of columns that take part, two at most, and holds no key verified of fewer columns; warned
of where its values are not unique, but the primary key all the same, as the overrides are of all
environments. Else it is the key of the fewest columns, then of whole numbers or UUIDs, as a
database generates keys, then the first in the table. The keys name columns alone, and no values of
the database.
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
# The pairs verified at most, and the keys indicated verified in one query at most.
_PAIRS: Final = 10
_PER_QUERY: Final = 10


def identify(source: Source, table: Table, sample: Sample, given: tuple[str, ...] | None) -> Table:
    """`table` with its keys, verified on the whole table, and its primary: given, else chosen.

    Args:
        source: The schema the table is in.
        table: The table, its rows counted and its columns with their statistics.
        sample: The sample of the table, with the values of each of its columns.
        given: The columns of the primary key the overrides give, of the table; None where they
            give none.

    Returns:
        The table with its keys, the fewer columns first, then by the places of their columns -
        the key given among them where it is one -, and its primary key: the one given, else the
        one chosen; none of either where no key indicated is unique and none is given, with no
        query where none is indicated and none is given.

    Raises:
        SourceError: The database fails to count the values of the keys indicated.
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
    indicated = singles + _pairs(table, paired, sample)
    places = {column.name: place for place, column in enumerate(table.columns)}
    ordered = None if given is None else tuple(sorted(given, key=places.__getitem__))
    asked = [*indicated, ordered] if ordered is not None and ordered not in indicated else indicated
    verified = _verified(source, table, asked)
    if ordered is not None and ordered not in verified:
        _logger.warning(
            "The overrides give the primary key of %s as %s, whose values are not unique",
            table.name,
            ", ".join(ordered),
        )
    # Of the keys indicated none holds another; the key given is one where it is of columns that
    # take part, two at most, as one indicated is, and holds none verified.
    took = {column.name for column in taking}
    keys = [
        key
        for key in verified
        if key in indicated
        or (len(key) <= 2 and took.issuperset(key) and not any(set(o) < set(key) for o in verified))
    ]
    keys.sort(key=lambda key: (len(key), [places[name] for name in key]))
    primary: PrimaryKey | None
    if ordered is not None:
        primary = PrimaryKey(columns=ordered, given=True)
    else:
        # The fewest columns, then of the types a database generates keys of, then the first.
        chosen = min(
            keys,
            key=lambda key: (
                len(key),
                not all(dialect.is_surrogate(table.column(name).type) for name in key),
            ),
            default=None,
        )
        primary = None if chosen is None else PrimaryKey(columns=chosen)
    _logger.info(
        "Identified the keys of %s: %d, the primary %s",
        table.name,
        len(keys),
        "none" if primary is None else ", ".join(primary.columns),
    )
    return replace(table, keys=tuple(keys), primary_key=primary)


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
    source: Source, table: Table, indicated: Sequence[tuple[str, ...]]
) -> list[tuple[str, ...]]:
    """Those of `indicated` whose values are unique in the whole table, in their order."""
    dialect = source.dialect
    step = f"verifying the keys of {source.name(table.name)}"
    verified = []
    for start in range(0, len(indicated), _PER_QUERY):
        batch = indicated[start : start + _PER_QUERY]
        expressions = [
            dialect.rows(),
            *(dialect.exactly_distinct([dialect.column(name) for name in key]) for key in batch),
        ]
        (row,) = source.query(dialect.select(expressions, table.name), step)
        rows, *distinct = (counted(found, table.name) for found in row)
        verified += [key for key, found in zip(batch, distinct, strict=True) if found == rows]
    return verified


def _unique(values: Iterable[object]) -> bool:
    """Whether no two of `values` are equal."""
    listed = list(values)
    return len(set(listed)) == len(listed)
