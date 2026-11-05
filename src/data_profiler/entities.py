"""The entities of a table: its rows told apart by the values of its discriminator.

A candidate is a column whose values the profile holds - an enumeration of no sensitivity - of two
values at least. The query, built from the building blocks of the dialect, groups the table by each
candidate on its own, in one pass, and counts the rows of each value and those of them each column
is filled in: where it holds a value, neither null nor one of the sentinels its statistics found.
Counted on the whole table, not in a sample, an entity of few rows is found as well, and each count
is exact.

A column tells two values apart where it is filled in at least `_MOST` of the rows of the one and in
at most `_LEAST` of the rows of the other, both of at least `_FEWEST` rows; two values are of two
entities where at least `_COLUMNS` columns tell them apart, so that a status whose one value fills a
column of a reason is no discriminator. The values of a candidate of enough rows, the most frequent
first, each join the first entity none of whose values they are of two entities with, or begin one
of their own; a value of too few rows to be told apart joins the entity whose columns are filled in
the shares closest to its own, the first of several. A candidate of two entities at least is a
discriminator; of several, the one whose entities the most columns tell apart, then the one of fewer
entities, then the first in the table. The rows of a value of a null, a sentinel or a value the
profile does not hold as it is - withheld, or cut where it is long - are of no entity. The values
are values of the database: they go into the profile as the profile holds the values of the
candidate, and never into the log.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import replace
from itertools import combinations
from typing import Final

from data_profiler.profile import Column, Discriminator, Entity, Table
from data_profiler.source import Source
from data_profiler.values import as_text, counted

_logger = logging.getLogger(__name__)

# The share of the rows of one value a column is filled in at least, and of the other at most, to
# tell the two apart; the rows each of them has at least; the columns that tell two values apart,
# at least, to make them two entities.
_MOST: Final = 0.9
_LEAST: Final = 0.1
_FEWEST: Final = 10
_COLUMNS: Final = 3

# The rows of a value, and those of them each column of the table is filled in, in its order.
type _Counts = tuple[int, tuple[int, ...]]


def discriminate(source: Source, table: Table) -> Table:
    """`table` with its discriminator, where one of its columns tells entities of its rows apart.

    Args:
        source: The schema the table is in.
        table: The table, its columns with their statistics and the values the profile holds.

    Returns:
        The table with its discriminator, or with none where no column tells entities apart; with
        no query where no column is a candidate.

    Raises:
        SourceError: The database fails to count the rows of the values.
    """
    candidates = [column for column in table.columns if len(column.values) > 1]
    found = []
    if candidates:
        counts = _count(source, table, candidates)
        names = [column.name for column in table.columns]
        for column in candidates:
            discriminator = _discriminator(column, counts[column.name], names)
            if discriminator is not None:
                found.append(discriminator)
    # The most columns that tell its entities apart, then the fewest entities, then the first.
    best = max(found, key=lambda pair: (pair[1], -len(pair[0].entities)), default=None)
    _logger.info(
        "Told the entities of %s apart: %s",
        table.name,
        "none" if best is None else f"{len(best[0].entities)} by {best[0].column}",
    )
    return replace(table, discriminator=None if best is None else best[0])


def _count(
    source: Source, table: Table, candidates: Sequence[Column]
) -> dict[str, dict[str, _Counts]]:
    """Of each of `candidates`, the counts of each of its values the profile holds, by its text."""
    dialect = source.dialect
    names = [column.name for column in candidates]
    expressions = [
        dialect.rows(),
        *(
            dialect.nulls(dialect.without(column.name, column.type, column.left_aside))
            for column in table.columns
        ),
    ]
    held = {column.name: {value.value for value in column.values} for column in candidates}
    by_column: dict[str, dict[str, _Counts]] = {name: {} for name in names}
    step = f"counting the entities of {source.name(table.name)}"
    for index, value, (rows, *nulls) in source.grouped(table.name, names, expressions, step):
        text = None if value is None else as_text(value)
        if text not in held[names[index]]:
            continue
        where = f"{table.name}.{names[index]}"
        present = counted(rows, where)
        filled = tuple(present - counted(empty, where) for empty in nulls)
        by_column[names[index]][text] = (present, filled)
    return by_column


def _discriminator(
    column: Column, counts: Mapping[str, _Counts], names: Sequence[str]
) -> tuple[Discriminator, int] | None:
    """`column` as the discriminator of the columns `names`, with how many tell its entities apart.

    None where the values of the column are of one entity.
    """
    held = [value.value for value in column.values if value.value in counts]
    entities: list[list[str]] = []
    for value in (value for value in held if counts[value][0] >= _FEWEST):
        joined = next(
            (
                entity
                for entity in entities
                if all(len(_apart(counts[value], counts[other])) < _COLUMNS for other in entity)
            ),
            None,
        )
        if joined is None:
            entities.append([value])
        else:
            joined.append(value)
    if len(entities) < 2:
        return None
    for value in (value for value in held if counts[value][0] < _FEWEST):
        closest = min(
            entities, key=lambda entity: _distance(counts[value], _joined(entity, counts))
        )
        closest.append(value)
    telling = set[int]().union(
        *(
            _apart(_joined(first, counts), _joined(second, counts))
            for first, second in combinations(entities, 2)
        )
    )
    made = sorted(
        (_entity(values, counts, names) for values in entities),
        key=lambda entity: entity.rows,
        reverse=True,
    )
    return Discriminator(column=column.name, entities=tuple(made)), len(telling)


def _joined(values: Sequence[str], counts: Mapping[str, _Counts]) -> _Counts:
    """The counts of the rows of all of `values` together."""
    filled = (sum(column) for column in zip(*(counts[value][1] for value in values), strict=True))
    return sum(counts[value][0] for value in values), tuple(filled)


def _entity(values: Sequence[str], counts: Mapping[str, _Counts], names: Sequence[str]) -> Entity:
    """The entity of the rows of `values`, with the rows each of the columns `names` is filled."""
    rows, filled = _joined(values, counts)
    return Entity(values=tuple(values), rows=rows, filled=dict(zip(names, filled, strict=True)))


def _apart(first: _Counts, second: _Counts) -> set[int]:
    """The columns, by their places, that tell the rows of `first` and of `second` apart."""
    (rows, filled), (other_rows, other_filled) = first, second
    return {
        index
        for index, (one, other) in enumerate(zip(filled, other_filled, strict=True))
        if _tells(one / rows, other / other_rows) or _tells(other / other_rows, one / rows)
    }


def _distance(first: _Counts, second: _Counts) -> float:
    """The sum over the columns of how far the shares of the rows they are filled in lie apart."""
    (rows, filled), (other_rows, other_filled) = first, second
    return sum(
        abs(one / rows - other / other_rows)
        for one, other in zip(filled, other_filled, strict=True)
    )


def _tells(filled: float, empty: float) -> bool:
    """Whether a column filled in the shares `filled` and `empty` of two sets of rows tells them."""
    return filled >= _MOST and empty <= _LEAST
