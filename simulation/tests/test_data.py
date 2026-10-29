"""Tests of the rows of test data: their columns have the statistics of the profile."""

from random import Random

import pytest

from data_profiler.profile import Column, Lengths, Statistics, Table
from simulation import SimulationError
from simulation.data import rows


def _table(*columns: Column, count: int = 1000) -> Table:
    """A table of `count` rows with `columns`."""
    return Table(name="t", rows=count, columns=columns)


def _column(
    name: str, type: str, nulls: int, distinct: int, lengths: Lengths | None = None
) -> Column:
    """A column of `type` with the given statistics."""
    return Column(name=name, type=type, statistics=Statistics(nulls, distinct, lengths))


_TABLE = _table(
    _column("id", "bigint", 0, 1000),
    _column("nm", "varchar(40)", 100, 750, Lengths(3, 30)),
    _column("cd", "varchar(2)", 0, 4, Lengths(1, 2)),
    _column("dt", "date", 300, 200),
    _column("ts", "timestamp(3)", 0, 990),
    _column("amt", "decimal(10,2)", 50, 80),
    _column("rt", "double", 0, 10),
    _column("qty", "integer", 0, 25),
    _column("pos", "smallint", 0, 9),
    _column("flg", "boolean", 10, 2),
)


def test_a_table_has_as_many_rows_as_its_profile_counts() -> None:
    assert len(rows(_TABLE, Random(0))) == _TABLE.rows


@pytest.mark.parametrize("index", range(len(_TABLE.columns)), ids=[c.name for c in _TABLE.columns])
def test_a_column_has_its_nulls_and_distinct_values(index: int) -> None:
    statistics = _TABLE.columns[index].statistics
    values = [row[index] for row in rows(_TABLE, Random(0))]
    assert values.count(None) == statistics.nulls
    assert len(set(values) - {None}) == statistics.distinct


def test_a_text_column_has_its_shortest_and_its_longest_value() -> None:
    values = [row[1] for row in rows(_TABLE, Random(0)) if row[1] is not None]
    lengths = {len(str(value)) for value in values}
    assert (min(lengths), max(lengths)) == (3, 30)


def test_the_same_seed_gives_the_same_rows() -> None:
    assert rows(_TABLE, Random(7)) == rows(_TABLE, Random(7))


@pytest.mark.parametrize(
    ("column", "problem"),
    [
        (_column("x", "varbinary", 0, 10), "the type varbinary is not generated"),
        (_column("x", "bigint", 10, 995), "do not fit 1000 rows"),
        (_column("x", "boolean", 0, 3), "fewer than 3 distinct values"),
        (_column("x", "varchar(1)", 0, 30, Lengths(1, 1)), "30 distinct values cannot be drawn"),
        (_column("x", "varchar(9)", 0, 30), "without its lengths"),
    ],
    ids=["an unknown type", "too many values", "too few booleans", "too few texts", "no lengths"],
)
def test_a_column_that_cannot_be_generated_is_refused_naming_it(
    column: Column, problem: str
) -> None:
    with pytest.raises(SimulationError, match=f"t.x: .*{problem}"):
        rows(_table(column), Random(0))
