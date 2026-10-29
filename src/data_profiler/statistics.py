"""The statistics of a table, counted by one query built from the building blocks of the dialect.

The query asks for the rows of the table, and for each column its nulls and the approximate number
of its distinct values, and for a column of texts the lengths of its shortest and of its longest
value. The row it returns is read along the same list of expressions it was built from, so that
its form is known in this module alone. No value of the database is counted into it.
"""

from itertools import chain

from data_profiler.profile import Column, Lengths, Statistics, Table
from data_profiler.source import Source


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
    asked = []
    for name, kind in source.columns(table).items():
        expressions = [dialect.nulls(name), dialect.distinct(name)]
        if dialect.is_text(kind):
            expressions += [dialect.shortest(name), dialect.longest(name)]
        asked.append((name, kind, expressions))
    statement = dialect.select(
        [dialect.rows(), *chain.from_iterable(e for _, _, e in asked)], table
    )
    (row,) = source.query(statement, f"counting the statistics of {source.name(table)}")
    values = iter(row)
    rows = _number(next(values), table)
    columns = []
    for name, kind, expressions in asked:
        counted = [next(values) for _ in expressions]
        statistics = _statistics(counted, f"{table}.{name}")
        columns.append(Column(name=name, type=kind, statistics=statistics))
    return Table(name=table, rows=rows, columns=tuple(columns))


def _statistics(counted: list[object], where: str) -> Statistics:
    """The statistics of the column `where`, from what its expressions counted, in their order."""
    nulls, distinct, *lengths = counted
    shortest, longest = lengths or (None, None)
    return Statistics(
        nulls=_number(nulls, where),
        distinct=_number(distinct, where),
        lengths=None
        if shortest is None
        else Lengths(_number(shortest, where), _number(longest, where)),
    )


def _number(value: object, where: str) -> int:
    """`value`, which the query has counted of `where`, as a number."""
    if not isinstance(value, int):
        raise TypeError(f"the query counted something of {where} that is no number")
    return value
