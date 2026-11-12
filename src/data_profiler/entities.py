"""The entities of a table: its rows told apart by the values of its discriminator.

A candidate is a column whose values the profile holds - an enumeration of no sensitivity - of two
values at least; of a column of lists, whose texts are no values of one, the values of its lists
are, `Column.as_items`. The query, built from the building blocks of the dialect, groups the table
by each candidate on its own, in one pass, and counts the rows of each value and those of them each
column is filled in: where it holds a value, neither null nor one of the sentinels its statistics
found. A candidate of lists is counted by a query of its own, of a source that reads the table as a
row of each value of its lists, `Source.unnested`, so that a row is counted with each value of its
list: the rows of an entity may be more than its own, of a list of two of its values, and those of
its entities more than those of the table. Counted on the whole table, not in a sample, an entity of
few rows is found as well, and each count is exact.

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

The overrides may give the discriminator of a table, and entities of it by their values: the query
then groups by its column alone, the values of each entity given are of it, whether or not columns
tell them apart, and the other values join those or each other as they would join entities found - a
value of enough rows compared with the values of enough rows of an entity alone, so that a value
given of too few rows tells nothing. The discriminator holds the values given that it was counted
with. The values given that the profile does not hold of the column are left out, and a column of
none of its values held gives a discriminator of no entities, both warned of, as the overrides are
the same for all environments, whose tables differ. Where the overrides give a table no
discriminator, it has none, whatever would be found.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import replace
from itertools import combinations
from typing import Final

from data_profiler.counts import counted
from data_profiler.overrides import DiscriminatorOverride, GivenDiscriminator
from data_profiler.profile import Column, Discriminator, Entity, Table
from data_profiler.source import Source

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


def discriminate(source: Source, table: Table, given: GivenDiscriminator) -> Table:
    """`table` with its discriminator: the one given, else the one found among its columns.

    Args:
        source: The schema the table is in.
        table: The table, its columns with their statistics and the values the profile holds.
        given: The discriminator the overrides give of the table, a column of values it holds;
            False where they give it none, whatever is found; None where they give nothing of it.

    Returns:
        The table with the discriminator given, of the entities given and those its other values
        are found of; else with the one found, or with none where no column tells entities apart.
        No query is sent where False is given, or none is given and no column is a candidate.

    Raises:
        SourceError: The database fails to list the columns of the table, to read the values of a
            list, or to count the rows of the values.
    """
    if given is False:
        discriminator = None
    elif given is None:
        discriminator = _found(source, table)
    else:
        discriminator = _given(source, table, given)
    told = (
        "none"
        if discriminator is None
        else f"{len(discriminator.entities)} by {discriminator.column}"
    )
    _logger.info("Told the entities of %s apart: %s", table.name, told)
    return replace(table, discriminator=discriminator)


def _found(source: Source, table: Table) -> Discriminator | None:
    """The discriminator of `table` found among its candidates, or None where none is one."""
    candidates = [column.as_items for column in table.columns if len(column.as_items.values) > 1]
    if not candidates:
        return None
    counts = _count(source, table, candidates)
    names = [column.name for column in table.columns]
    found = []
    for column in candidates:
        discriminator = _discriminator(column, counts[column.name], names)
        if discriminator is not None:
            found.append(discriminator)
    # The most columns that tell its entities apart, then the fewest entities, then the first.
    best = max(found, key=lambda pair: (pair[1], -len(pair[0].entities)), default=None)
    return None if best is None else best[0]


def _given(source: Source, table: Table, given: DiscriminatorOverride) -> Discriminator:
    """The discriminator `given` of `table`, of no entities where its column holds no value counted.

    A column of no values the profile holds, and the values given that it does not hold, are warned
    of, the values left out, as the overrides are of all environments, whose tables differ; the
    discriminator records the values given all the same, as the table was counted with them.
    """
    column = table.column(given.column).as_items
    held = {value.value for value in column.values}
    if not held:
        _logger.warning(
            "The overrides give the discriminator of %s as %s, of which the profile holds no"
            " values: it has no entities",
            table.name,
            column.name,
        )
        return Discriminator(column=column.name, entities=(), given=given.values)
    unheld = [name for name, entity in given.entities.items() if not set(entity.values) <= held]
    if unheld:
        _logger.warning(
            "The overrides give entities of %s values the profile does not hold of %s, which are"
            " left out: %s",
            table.name,
            column.name,
            ", ".join(unheld),
        )
    counts = _count(source, table, [column])[column.name]
    entities = _grouped(column, counts, given.values)
    names = [column.name for column in table.columns]
    return Discriminator(
        column=column.name, entities=_made(entities, counts, names), given=given.values
    )


def _count(
    source: Source, table: Table, candidates: Sequence[Column]
) -> dict[str, dict[str, _Counts]]:
    """Of each of `candidates`, the counts of each of its values the profile holds, by its text.

    A candidate of the values of the lists of a column of `table` - of its items - is counted on a
    source of a row of each of them, each on its own; the others in one query.
    """
    counts: dict[str, dict[str, _Counts]] = {}
    plain = []
    for column in candidates:
        separator = table.column(column.name).items_separator
        if separator is None:
            plain.append(column)
        else:
            unnested = source.unnested(table.name, column.name, separator)
            counts |= _count_on(unnested, table, [column])
    return (_count_on(source, table, plain) if plain else {}) | counts


def _count_on(
    source: Source, table: Table, candidates: Sequence[Column]
) -> dict[str, dict[str, _Counts]]:
    """Of each of `candidates`, the counts of its values the profile holds, by one query."""
    dialect = source.dialect
    columns = {column.name: column.type for column in candidates}
    expressions = [
        dialect.rows(),
        *(
            dialect.nulls(dialect.without(column.name, column.type, column.left_aside))
            for column in table.columns
        ),
    ]
    held = {column.name: {value.value for value in column.values} for column in candidates}
    by_column: dict[str, dict[str, _Counts]] = {name: {} for name in columns}
    step = f"counting the entities of {source.name(table.name)}"
    for name, value, (rows, *nulls) in source.grouped(table.name, columns, expressions, step):
        text = None if value is None else str(value)
        if text not in held[name]:
            continue
        where = f"{table.name}.{name}"
        present = counted(rows, where)
        filled = tuple(present - counted(empty, where) for empty in nulls)
        by_column[name][text] = (present, filled)
    return by_column


def _discriminator(
    column: Column, counts: Mapping[str, _Counts], names: Sequence[str]
) -> tuple[Discriminator, int] | None:
    """`column` as the discriminator of the columns `names`, with how many tell its entities apart.

    None where the values of the column are of one entity.
    """
    entities = _grouped(column, counts, ())
    if len(entities) < 2:
        return None
    telling = set[int]().union(
        *(
            _apart(_joined(first, counts), _joined(second, counts))
            for first, second in combinations(entities, 2)
        )
    )
    return Discriminator(column=column.name, entities=_made(entities, counts, names)), len(telling)


def _grouped(
    column: Column, counts: Mapping[str, _Counts], given: Sequence[Sequence[str]]
) -> list[list[str]]:
    """The values of `column` counted, as the values of its entities: those `given` first.

    Each entity given keeps those of its values that are counted; the other values, of enough rows,
    the most frequent first, each join the first entity of a value of enough rows none of whose
    values of enough rows they are of two entities with, or begin one of their own; a value of too
    few rows joins the entity closest to it, or begins one where there is none.
    """
    entities = [[value for value in values if value in counts] for values in given]
    entities = [entity for entity in entities if entity]
    taken = {value for entity in entities for value in entity}
    others = [v.value for v in column.values if v.value in counts and v.value not in taken]
    for value in (value for value in others if counts[value][0] >= _FEWEST):
        joined = next((entity for entity in entities if _joins(value, entity, counts)), None)
        if joined is None:
            entities.append([value])
        else:
            joined.append(value)
    for value in (value for value in others if counts[value][0] < _FEWEST):
        closest = min(
            entities,
            key=lambda entity: _distance(counts[value], _joined(entity, counts)),
            default=None,
        )
        if closest is None:
            entities.append([value])
        else:
            closest.append(value)
    return entities


def _joins(value: str, entity: Sequence[str], counts: Mapping[str, _Counts]) -> bool:
    """Whether `value` joins `entity`: of one entity with each of its values of enough rows."""
    told = [other for other in entity if counts[other][0] >= _FEWEST]
    return bool(told) and all(len(_apart(counts[value], counts[o])) < _COLUMNS for o in told)


def _made(
    entities: Sequence[Sequence[str]], counts: Mapping[str, _Counts], names: Sequence[str]
) -> tuple[Entity, ...]:
    """The entities of the rows of the values of each of `entities`, the one of most rows first."""
    made = (_entity(values, counts, names) for values in entities)
    return tuple(sorted(made, key=lambda entity: entity.rows, reverse=True))


def _joined(values: Sequence[str], counts: Mapping[str, _Counts]) -> _Counts:
    """The counts of the rows of all of `values` together."""
    filled = (sum(column) for column in zip(*(counts[value][1] for value in values), strict=True))
    return sum(counts[value][0] for value in values), tuple(filled)


def _entity(values: Sequence[str], counts: Mapping[str, _Counts], names: Sequence[str]) -> Entity:
    """The entity of the rows of `values`, with the rows each of the columns `names` is filled."""
    rows, filled = _joined(values, counts)
    ordered = sorted(values, key=lambda value: counts[value][0], reverse=True)
    return Entity(values=tuple(ordered), rows=rows, filled=dict(zip(names, filled, strict=True)))


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
