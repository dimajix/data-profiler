"""The statistics of a table, counted by one query built from the building blocks of the dialect.

The query asks for the rows of the table, and for each column its nulls and the approximate number
of its distinct values, for a column whose values have an order its smallest and its largest value,
and for a column of texts the lengths of its shortest and of its longest value. The row it returns
is read along the same list of expressions it was built from, so that its form is known in this
module alone. The range of a column is of values of the database; whether it goes into the profile,
the module `disclosure` decides.
"""

from itertools import chain

from data_profiler.profile import Column, Lengths, Range, Statistics, Table
from data_profiler.source import Source, as_text, counted


def count(source: Source, table: str) -> Table:
    """The table `table` of `source`, its columns with their types and statistics.

    Args:
        source: The schema the table is in.
        table: The name of the table.

    Returns:
        The table, its rows counted, its columns in their order.

    Raises:
        SourceError: The schema has no such table, or the database fails to count it.
    """
    dialect = source.dialect
    # Of each column, the expressions of each group of its statistics; a group that is not asked
    # for has none.
    asked = []
    for name, kind in source.columns(table).items():
        of_counts = [dialect.nulls(name), dialect.distinct(name)]
        of_range = (
            [dialect.smallest(name), dialect.largest(name)] if dialect.is_ordered(kind) else []
        )
        of_lengths = (
            [dialect.shortest(name), dialect.longest(name)] if dialect.is_text(kind) else []
        )
        asked.append((name, kind, (of_counts, of_range, of_lengths)))
    expressions = chain.from_iterable(chain.from_iterable(groups) for _, _, groups in asked)
    statement = dialect.select([dialect.rows(), *expressions], table)
    (row,) = source.query(statement, f"counting the statistics of {source.name(table)}")
    values = iter(row)
    rows = counted(next(values), table)
    columns = []
    for name, kind, groups in asked:
        counts, ranged, lengths = ([next(values) for _ in group] for group in groups)
        statistics = _statistics(counts, ranged, lengths, f"{table}.{name}")
        columns.append(Column(name=name, type=kind, statistics=statistics))
    return Table(name=table, rows=rows, columns=tuple(columns))


def _statistics(
    counts: list[object], ranged: list[object], lengths: list[object], where: str
) -> Statistics:
    """The statistics of the column `where`, from what each group of its expressions counted.

    A group that was not asked for, or that holds nulls only, as of a column of nulls, is None.
    """
    nulls, distinct = counts
    smallest, largest = ranged or (None, None)
    shortest, longest = lengths or (None, None)
    return Statistics(
        nulls=counted(nulls, where),
        distinct=counted(distinct, where),
        lengths=None
        if shortest is None
        else Lengths(counted(shortest, where), counted(longest, where)),
        range=None if smallest is None else Range(as_text(smallest), as_text(largest)),
    )
