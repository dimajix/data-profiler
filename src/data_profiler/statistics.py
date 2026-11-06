"""The statistics of a table, counted by one query built from the building blocks of the dialect.

The query asks for the rows of the table, and for each column its nulls, the rows of each of its
sentinels and the approximate number of its distinct values, for a column whose values have an
order its smallest and its largest value, and for a column of texts the lengths of its shortest and
of its longest value. The sentinels of a column are those of the tool, or those given of it by
hand, each counted apart, so that a person sees which a column has; what is counted of its values
leaves them aside, but its nulls. A column whose values the database writes as no text - an array,
a map, a binary - has no sentinels. The row the query returns is read along the same list of
expressions it was built from, so that its form is known in this module alone. The range of a
column is of values of the database; whether it goes into the profile, the module `disclosure`
decides.
"""

from collections.abc import Collection, Iterable, Mapping
from itertools import chain

from data_profiler.detect import sentinels
from data_profiler.profile import Column, Lengths, Range, Statistics, Table, Value
from data_profiler.source import Source
from data_profiler.values import as_text, counted


def count(
    source: Source,
    table: str,
    given: Mapping[str, tuple[str, ...]],
    columns: Collection[str] | None = None,
) -> Table:
    """The table `table` of `source`, its columns with their types and statistics.

    Args:
        source: The schema the table is in.
        table: The name of the table.
        columns: The columns to count, by their names, all of the table where None; the table
            holds those alone.
        given: The sentinels given by hand of its columns, by their names, in place of those of
            the tool; a column not named has those of the tool.

    Returns:
        The table, its rows counted, its columns in their order, each with the sentinels given of
        it where it has text, and none given where it has none.

    Raises:
        SourceError: The schema has no such table, or the database fails to count it.
    """
    dialect = source.dialect
    # Of each column, the sentinels given it was counted with, the sentinels counted, and the
    # expressions of each group of its statistics; a group that is not asked for has none.
    asked = []
    for name, kind in source.columns(table).items():
        if columns is not None and name not in columns:
            continue
        has_text = dialect.has_text(kind)
        counted_with = given.get(name) if has_text else None
        texts = sentinels(counted_with) if has_text else frozenset()
        values = dialect.column(name)
        kept = dialect.without(name, kind, texts)
        of_counts = [dialect.nulls(values), dialect.distinct(kept)]
        listed = sorted(texts)
        of_sentinels = [dialect.sentinels(name, kind, {text}) for text in listed]
        of_range = (
            [dialect.smallest(kept), dialect.largest(kept)] if dialect.is_ordered(kind) else []
        )
        of_lengths = (
            [dialect.shortest(kept), dialect.longest(kept)] if dialect.is_text(kind) else []
        )
        groups = (of_counts, of_sentinels, of_range, of_lengths)
        asked.append((name, kind, counted_with, listed, groups))
    expressions = chain.from_iterable(chain.from_iterable(groups) for *_, groups in asked)
    statement = dialect.select([dialect.rows(), *expressions], table)
    (row,) = source.query(statement, f"counting the statistics of {source.name(table)}")
    answers = iter(row)
    rows = counted(next(answers), table)
    found_columns = []
    for name, kind, counted_with, listed, groups in asked:
        counts, found, ranged, lengths = ([next(answers) for _ in group] for group in groups)
        statistics = _statistics(
            counts, zip(listed, found, strict=True), ranged, lengths, f"{table}.{name}"
        )
        found_columns.append(
            Column(name=name, type=kind, statistics=statistics, sentinels=counted_with)
        )
    return Table(name=table, rows=rows, columns=tuple(found_columns))


def _statistics(
    counts: list[object],
    found: Iterable[tuple[str, object]],
    ranged: list[object],
    lengths: list[object],
    where: str,
) -> Statistics:
    """The statistics of the column `where`, from what each group of its expressions counted.

    A group that was not asked for, or that holds nulls only, as of a column of nulls, is None;
    `found` are the sentinels asked for, each with its rows, of which those of none are left out.
    """
    nulls, distinct = counts
    rows = ((text, counted(number, where)) for text, number in found)
    sentinels = sorted((Value(text, number) for text, number in rows if number), key=_most)
    smallest, largest = ranged or (None, None)
    shortest, longest = lengths or (None, None)
    return Statistics(
        nulls=counted(nulls, where),
        distinct=counted(distinct, where),
        lengths=None
        if shortest is None
        else Lengths(counted(shortest, where), counted(longest, where)),
        range=None if smallest is None else Range(as_text(smallest), as_text(largest)),
        sentinels=tuple(sentinels),
    )


def _most(value: Value) -> tuple[int, str]:
    """The order of the sentinels of a column: the most frequent first, else by their texts."""
    return -value.rows, value.value
