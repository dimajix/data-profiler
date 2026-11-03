"""Tests of the rows of test data: their columns have the statistics of the profile."""

from datetime import date, datetime
from random import Random

import pytest

from data_profiler.detect import (
    BUILT_IN,
    CARD_NUMBER,
    DATE,
    EMAIL,
    FREE_TEXT,
    IBAN,
    PHONE,
    POSTAL_CODE,
    TRUE_FALSE,
    UUID,
    YES_NO,
    ZERO_ONE,
    SemanticType,
)
from data_profiler.profile import Column, Lengths, Match, Statistics, Table, Value
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
    Column(
        name="iban",
        type="varchar(34)",
        statistics=Statistics(400, 500, Lengths(22, 27)),
        matches=(Match(IBAN, 1.0),),
    ),
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


@pytest.mark.parametrize(
    ("type", "lengths", "texts", "made"),
    [
        ("varchar(10)", Lengths(5, 5), ("", "N/A"), ("", "N/A")),
        ("date", None, ("9999-12-31",), (date(9999, 12, 31),)),
        ("timestamp(3)", None, ("9999-12-31",), (datetime(9999, 12, 31),)),
    ],
    ids=["a text", "a day", "a moment"],
)
def test_a_column_has_each_of_its_sentinels_beside_its_nulls(
    type: str, lengths: Lengths | None, texts: tuple[str, ...], made: tuple[object, ...]
) -> None:
    counted = tuple(Value(text, 300) for text in texts)
    statistics = Statistics(100, 50, lengths, sentinels=counted)
    table = _table(Column(name="x", type=type, statistics=statistics))
    values = [value for (value,) in rows(table, Random(0))]
    assert [values.count(sentinel) for sentinel in made] == [300] * len(made)
    assert values.count(None) == 100
    assert len(set(values) - {None, *made}) == 50


# A sentinel of five rows, which is no day.
_NONE = (Value("N/A", 5),)


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
        (
            Column(name="x", type="bigint", statistics=Statistics(0, 10, sentinels=_NONE)),
            "no sentinel of bigint is made",
        ),
        (
            Column(name="x", type="date", statistics=Statistics(0, 10, sentinels=_NONE)),
            "a sentinel is no day",
        ),
    ],
    ids=[
        "an unknown type",
        "too many values",
        "too few booleans",
        "too few texts",
        "no lengths",
        "no sentinel",
        "no day",
    ],
)
def test_a_column_that_cannot_be_generated_is_refused_naming_it(
    column: Column, problem: str
) -> None:
    with pytest.raises(SimulationError, match=f"t.x: .*{problem}"):
        rows(_table(column), Random(0))


# The shortest and the longest text of each semantic type of the tool that is made, and how many
# distinct texts of 500 a column of them has: as many as there are, as the condition of free text
# wants half of its values of words distinct, and of a pair two.
_TEXTS = {
    EMAIL: (11, 44, 500),
    PHONE: (9, 16, 500),
    POSTAL_CODE: (5, 5, 500),
    IBAN: (22, 27, 500),
    CARD_NUMBER: (13, 19, 500),
    DATE: (10, 19, 500),
    UUID: (36, 36, 500),
    FREE_TEXT: (12, 60, 500),
    TRUE_FALSE: (4, 5, 2),
    YES_NO: (2, 3, 2),
    ZERO_ONE: (1, 1, 2),
}


def test_every_semantic_type_of_the_tool_is_made() -> None:
    assert set(_TEXTS) == set(BUILT_IN), "a type of the tool without a test of its texts"


@pytest.mark.parametrize(
    ("kind", "shortest", "longest", "distinct"),
    [pytest.param(kind, *texts, id=kind.name) for kind, texts in _TEXTS.items()],
)
def test_a_text_of_a_semantic_type_is_recognised_by_its_detector(
    kind: SemanticType, shortest: int, longest: int, distinct: int
) -> None:
    column = Column(
        name="v",
        type="varchar(60)",
        statistics=Statistics(0, distinct, Lengths(shortest, longest)),
        matches=(Match(kind, 1.0),),
    )
    values = [str(value) for (value,) in rows(_table(column, count=500), Random(0))]
    assert kind.detector.share(values) == 1.0, "every text is of the type, and so is the column"
    assert (min(map(len, values)), max(map(len, values))) == (shortest, longest)


def test_a_text_of_a_semantic_type_of_a_project_is_refused(account_number: SemanticType) -> None:
    column = Column(
        name="v",
        type="varchar(11)",
        statistics=Statistics(0, 10, Lengths(11, 11)),
        matches=(Match(account_number, 1.0),),
    )
    with pytest.raises(SimulationError, match=r"t\.v: no account-number is made"):
        rows(_table(column, count=10), Random(0))


def test_a_column_whose_values_fail_the_condition_of_their_type_together_is_refused() -> None:
    column = Column(
        name="v",
        type="varchar(60)",
        statistics=Statistics(0, 10, Lengths(12, 60)),
        matches=(Match(FREE_TEXT, 1.0),),
    )
    with pytest.raises(SimulationError, match=r"t\.v: 10 distinct values of 500 are no free-text"):
        rows(_table(column, count=500), Random(0))


def test_a_text_of_a_semantic_type_that_no_value_has_the_length_of_is_refused() -> None:
    column = Column(
        name="v",
        type="varchar(10)",
        statistics=Statistics(0, 10, Lengths(4, 6)),
        matches=(Match(POSTAL_CODE, 1.0),),
    )
    with pytest.raises(SimulationError, match=r"t\.v: no postal-code of 4 characters can be made"):
        rows(_table(column, count=10), Random(0))
