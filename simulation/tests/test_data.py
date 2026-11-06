"""Tests of the rows of test data: their columns have the statistics of the profile."""

import re
from dataclasses import replace
from datetime import date, datetime

import pytest

from data_profiler.currencies import CODES, NUMBERS
from data_profiler.detect import (
    BUILT_IN,
    CARD_NUMBER,
    CURRENCY_CODE,
    CURRENCY_NAME,
    CURRENCY_NUMBER,
    DATE,
    EMAIL,
    FREE_TEXT,
    IBAN,
    PHONE,
    POSTAL_CODE,
    SENTINELS,
    TRUE_FALSE,
    UUID,
    YES_NO,
    ZERO_ONE,
    SemanticType,
    is_list,
)
from data_profiler.profile import (
    Column,
    ColumnDependency,
    ColumnGroup,
    Discriminator,
    Entity,
    Findings,
    Lengths,
    Match,
    Profile,
    Range,
    Reference,
    Statistics,
    Table,
    Value,
)
from simulation import SimulationError
from simulation.data import rows


def _profile(*tables: Table) -> Profile:
    """A profile of `tables`, which the references of a table refer to."""
    return Profile(catalog="crm", schema="sales", tables=tables)


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
    assert len(rows(_TABLE, _profile(), 0)) == _TABLE.rows


@pytest.mark.parametrize("index", range(len(_TABLE.columns)), ids=[c.name for c in _TABLE.columns])
def test_a_column_has_its_nulls_and_distinct_values(index: int) -> None:
    statistics = _TABLE.columns[index].statistics
    values = [row[index] for row in rows(_TABLE, _profile(), 0)]
    assert values.count(None) == statistics.nulls
    assert len(set(values) - {None}) == statistics.distinct


def test_a_text_column_has_its_shortest_and_its_longest_value() -> None:
    values = [row[1] for row in rows(_TABLE, _profile(), 0) if row[1] is not None]
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
    values = [value for (value,) in rows(table, _profile(), 0)]
    assert [values.count(sentinel) for sentinel in made] == [300] * len(made)
    assert values.count(None) == 100
    assert len(set(values) - {None, *made}) == 50


def test_the_columns_of_a_group_are_filled_in_the_same_rows_as_far_as_they_can_be() -> None:
    table = Table(
        name="t",
        rows=1000,
        columns=(
            _column("strt", "varchar(10)", 600, 50, Lengths(5, 5)),
            Column(
                "pst", "varchar(5)", Statistics(0, 50, Lengths(5, 5), sentinels=(Value("", 600),))
            ),
            _column("cty", "varchar(10)", 620, 50, Lengths(5, 5)),
            _column("other", "varchar(10)", 600, 50, Lengths(5, 5)),
        ),
        column_groups=(ColumnGroup(("strt", "pst", "cty"), 0.967),),
    )
    made = rows(table, _profile(), 0)
    strt, pst, cty, other = (
        {row for row, values in enumerate(made) if values[index] not in (None, "")}
        for index in range(4)
    )
    assert strt == pst, "the empty texts of a column are not filled either"
    assert cty < strt, "filled in fewer rows, within those of the others"
    assert other != strt, "a column of no group is filled in rows of its own"


def test_a_column_that_follows_from_another_is_made_of_its_values() -> None:
    table = Table(
        name="t",
        rows=1000,
        columns=(
            Column(
                "of", "varchar(5)", Statistics(0, 40, Lengths(5, 5), sentinels=(Value("", 100),))
            ),
            _column("code", "varchar(3)", 100, 40, Lengths(3, 3)),
            _column("half", "integer", 100, 20),
            _column("other", "integer", 0, 20),
        ),
        column_dependencies=(ColumnDependency(("of", "code"), ("half",), 1.0),),
    )
    made = rows(table, _profile(), 0)
    of, code, half, other = (
        {value[0]: {row[index] for row in made if row[0] == value[0]} for value in made}
        for index in range(4)
    )
    assert of[""] == {""} and code[""] == half[""] == {None}, "null where it is not filled"
    assert all(len(found) == 1 for found in [*code.values(), *half.values()]), "of one value each"
    assert len({next(iter(found)) for found in code.values()}) == 41, "code by code, and null"
    assert any(len(found) > 1 for found in other.values()), "a column of no dependency"


@pytest.mark.parametrize(
    ("dependent", "message"),
    [
        (_column("half", "integer", 0, 20), "does not follow from of"),
        (_column("half", "integer", 100, 50), "does not follow from of"),
    ],
    ids=["of other nulls", "of more values"],
)
def test_a_column_that_cannot_follow_from_another_is_refused(
    dependent: Column, message: str
) -> None:
    table = Table(
        name="t",
        rows=1000,
        columns=(_column("of", "integer", 100, 40), dependent),
        column_dependencies=(ColumnDependency(("of",), ("half",), 1.0),),
    )
    with pytest.raises(SimulationError, match=message):
        rows(table, _profile(), 0)


def test_a_column_follows_from_one_that_follows_from_another_made_before_it() -> None:
    table = Table(
        name="t",
        rows=1000,
        columns=(
            _column("half", "integer", 0, 20),
            _column("third", "integer", 0, 10),
            _column("of", "integer", 0, 40),
        ),
        column_dependencies=(
            ColumnDependency(("half",), ("third",), 1.0),
            ColumnDependency(("of",), ("half", "third"), 1.0),
        ),
    )
    made = rows(table, _profile(), 0)
    thirds = {half: {row[1] for row in made if row[0] == half} for half, *_ in made}
    assert all(len(found) == 1 for found in thirds.values()), "of the halves as they are made"


@pytest.mark.parametrize(
    ("changed", "message"),
    [
        ({"keys": (("half",),)}, "t.half: a key, reference or grouped column follows"),
        (
            {"references": (Reference("half", "t", "of", 1.0),)},
            "t.half: a key, reference or grouped column follows",
        ),
        (
            {"column_groups": (ColumnGroup(("of", "half"), 1.0),)},
            "t.half: a key, reference or grouped column follows",
        ),
        (
            {
                "column_dependencies": (
                    ColumnDependency(("of",), ("half",), 1.0),
                    ColumnDependency(("half",), ("of",), 1.0),
                )
            },
            "follows from itself",
        ),
    ],
    ids=["a key", "a reference", "a grouped column", "of itself"],
)
def test_a_column_that_follows_from_another_as_it_is_not_made_is_refused(
    changed: dict[str, object], message: str
) -> None:
    table = Table(
        name="t",
        rows=1000,
        columns=(_column("of", "integer", 0, 40), _column("half", "integer", 0, 20)),
        column_dependencies=(ColumnDependency(("of",), ("half",), 1.0),),
    )
    with pytest.raises(SimulationError, match=message):
        rows(replace(table, **changed), _profile(table), 0)  # type: ignore[arg-type]  # fields


def test_a_column_that_follows_from_another_in_a_table_of_entities_is_refused() -> None:
    table = _entities(Entity(("A",), 500, {"kind": 500, "own": 400}))
    dependent = replace(table, column_dependencies=(ColumnDependency(("own",), ("kind",), 1.0),))
    with pytest.raises(SimulationError, match="follows from another in a table of entities"):
        rows(dependent, _profile(), 0)


def _entities(*entities: Entity, nulls: int = 100) -> Table:
    """A table of 1000 rows of `entities`, told apart by `kind`, of the values A, B and C.

    Its column `own` is filled in 400 rows, `kind` in all but `nulls`.
    """
    kind = Column(
        "kind",
        "varchar(1)",
        Statistics(nulls, 3, Lengths(1, 1)),
        values=(Value("A", 500), Value("B", 300), Value("C", 100)),
    )
    own = _column("own", "varchar(5)", 600, 50, Lengths(5, 5))
    return replace(_table(kind, own), discriminator=Discriminator("kind", entities))


def test_the_rows_of_an_entity_hold_its_values_and_its_columns_as_it_counts_them() -> None:
    table = _entities(
        Entity(("A", "C"), 600, {"kind": 600, "own": 350}),
        Entity(("B",), 300, {"kind": 300, "own": 0}),
    )
    made = rows(table, _profile(), 0)
    kinds = [kind for kind, _ in made]
    assert [kinds.count(value) for value in ("A", "B", "C", None)] == [500, 300, 100, 100]
    filled = [kind for kind, own in made if own is not None]
    assert (filled.count("A") + filled.count("C"), filled.count("B")) == (350, 0)
    assert filled.count(None) == 50, "the rest of its rows in the rows of no entity"


@pytest.mark.parametrize(
    ("entities", "problem"),
    [
        ((Entity(("A",), 600, {"kind": 600, "own": 0}),), "not its own"),
        (
            (
                Entity(("A", "C"), 600, {"kind": 600, "own": 700}),
                Entity(("B",), 300, {"kind": 300, "own": 0}),
            ),
            "filled in 700 rows",
        ),
    ],
    ids=["rows of other values", "filled in more rows"],
)
def test_entities_that_cannot_be_generated_are_refused_naming_the_column(
    entities: tuple[Entity, ...], problem: str
) -> None:
    with pytest.raises(SimulationError, match=f"t\\.(kind|own): .*{problem}"):
        rows(_entities(*entities), _profile(), 0)


def test_the_nulls_of_a_discriminator_are_to_be_the_rows_of_no_entity() -> None:
    table = _entities(Entity(("A", "B", "C"), 900, {"kind": 900, "own": 400}), nulls=50)
    with pytest.raises(SimulationError, match=r"t\.kind: its nulls and sentinels are not"):
        rows(table, _profile(), 0)


def _keyed(order: int = 300, position: int = 5, nulls: int = 0, of_order: int = 0) -> Table:
    """A table of 1000 rows of a key of two columns, of `order` orders and `position` positions.

    The positions have `nulls`, the orders `of_order`.
    """
    keyed = _table(
        _column("ord", "bigint", of_order, order), _column("pos", "smallint", nulls, position)
    )
    return replace(keyed, keys=(("ord", "pos"),))


def test_a_key_of_two_columns_is_unique_each_column_of_its_distinct_values() -> None:
    made = rows(_keyed(), _profile(), 0)
    assert len(set(made)) == 1000, "no pair twice"
    assert (len({order for order, _ in made}), len({pos for _, pos in made})) == (300, 5)


@pytest.mark.parametrize(
    ("table", "problem"),
    [
        (_keyed(order=150), "150 values of 5 rows at most do not fill 1000 rows"),
        (_keyed(nulls=10), "a column of a key has nulls or sentinels"),
        (_keyed(of_order=10), "a column of a key has nulls or sentinels"),
    ],
    ids=["too few", "nulls", "nulls of the other"],
)
def test_a_key_of_two_columns_that_cannot_be_generated_is_refused(
    table: Table, problem: str
) -> None:
    with pytest.raises(SimulationError, match=f"t\\.(ord|pos): {problem}"):
        rows(table, _profile(), 0)


def _ranged(name: str, type: str, distinct: int, smallest: int, largest: int) -> Column:
    """A column of `type` of no nulls, of `distinct` values from `smallest` to `largest`."""
    statistics = Statistics(0, distinct, range=Range(str(smallest), str(largest)))
    return Column(name=name, type=type, statistics=statistics)


def test_whole_numbers_of_a_range_are_within_it_of_both_its_ends() -> None:
    table = _table(_ranged("v", "integer", 25, 1, 100))
    values = {value for (value,) in rows(table, _profile(), 0)}
    assert len(values) == 25
    assert {1, 100} <= values <= set(range(1, 101))


def test_whole_numbers_as_many_as_their_range_are_all_of_it() -> None:
    table = _table(_ranged("v", "smallint", 9, 1, 9))
    assert {value for (value,) in rows(table, _profile(), 0)} == set(range(1, 10)), (
        "numbered from one"
    )


def test_a_range_of_fewer_values_than_counted_is_refused() -> None:
    with pytest.raises(SimulationError, match=r"t\.v: 25 distinct values do not fit their range"):
        rows(_table(_ranged("v", "integer", 25, 1, 10)), _profile(), 0)


def test_uuids_are_made_of_their_type() -> None:
    column = _column("v", "uuid", 0, 1000)
    values = {value for (value,) in rows(_table(column), _profile(), 0)}
    assert len(values) == 1000
    assert all(UUID.detector.recognises(str(value)) for value in values)


_CUST = Table(
    name="cust",
    rows=500,
    columns=(
        _ranged("id", "bigint", 500, 1, 500),
        Column(name="key", type="varchar(36)", statistics=Statistics(0, 500, Lengths(36, 36))),
    ),
)


def _referring(key: str = "id", coverage: float | None = 1.0, distinct: int = 300) -> Table:
    """A table `ord` of 1000 rows whose column `cust`, of 100 nulls, refers to `key` of `cust`."""
    kind = _CUST.column(key).type
    referring = _column("cust", kind, 100, distinct, Lengths(36, 36))
    reference = Reference("cust", "cust", key, coverage)
    return replace(_table(referring), name="ord", references=(reference,))


def test_a_column_of_a_reference_holds_values_of_its_key_as_many_rows_as_it_covers() -> None:
    made = [
        value
        for (value,) in rows(_referring(coverage=0.9), _profile(_CUST), 0)
        if value is not None
    ]
    keys = {value for (value, _) in rows(_CUST, _profile(), 0)}
    found = [value for value in made if value in keys]
    assert len(set(made)) == 300
    assert len(found) == 810, "nine of ten rows of the 900 filled"
    assert all(isinstance(value, int) and value > 500 for value in set(made) - keys), (
        "those outside above the largest of the key"
    )


def test_a_column_of_lists_of_a_reference_holds_lists_of_values_of_its_key() -> None:
    listed = Column(
        name="custs",
        type="varchar(20)",
        statistics=Statistics(100, 300, Lengths(1, 11)),
        list_separator=";",
        items=Findings(Statistics(0, 40, Lengths(1, 3))),
    )
    reference = Reference("custs", "cust", "id", 1.0)
    table = replace(_table(listed), name="ord", references=(reference,))
    made = [str(value) for (value,) in rows(table, _profile(_CUST), 0) if value is not None]
    keys = {str(value) for (value, _) in rows(_CUST, _profile(), 0)}
    values = {value for text in made for value in text.split(";")}
    assert len(values) == 40
    assert values <= keys, "values of the key, as text"


@pytest.mark.parametrize(
    ("items", "lengths", "problem"),
    [
        (Statistics(0, 600, Lengths(1, 3)), Lengths(1, 11), "600 values of lists of 1 to 3"),
        (Statistics(0, 40, Lengths(4, 6)), Lengths(4, 11), "40 values of lists of 4 to 6"),
        (Statistics(0, 40), Lengths(1, 11), "a column of lists without the lengths of its items"),
    ],
    ids=["more values than the key", "of lengths the key has none of", "of no lengths"],
)
def test_a_column_of_lists_of_a_reference_that_cannot_be_made_is_refused(
    items: Statistics, lengths: Lengths, problem: str
) -> None:
    listed = Column(
        name="custs",
        type="varchar(20)",
        statistics=Statistics(0, 30, lengths),
        list_separator=";",
        items=Findings(items),
    )
    table = replace(_table(listed), name="ord", references=(Reference("custs", "cust", "id", 1.0),))
    with pytest.raises(SimulationError, match=f"ord\\.custs: {problem}"):
        rows(table, _profile(_CUST), 0)


def test_a_column_of_lists_of_lengths_no_list_of_its_values_is_of_is_refused() -> None:
    column = Column(
        name="v",
        type="varchar(15)",
        statistics=Statistics(0, 30, Lengths(3, 14)),
        list_separator=";",
        items=Findings(Statistics(0, 6, Lengths(3, 3)), matches=(Match(CURRENCY_CODE, 1.0),)),
    )
    with pytest.raises(SimulationError, match=r"t\.v: no list of 3 or 14 characters can be made"):
        rows(_table(column, count=100), _profile(), 0)


def test_a_column_of_lists_of_a_reference_of_values_outside_of_its_key_is_refused() -> None:
    listed = Column(
        name="custs",
        type="varchar(20)",
        statistics=Statistics(0, 30, Lengths(1, 11)),
        list_separator=";",
        items=Findings(Statistics(0, 40, Lengths(1, 3))),
    )
    table = replace(_table(listed), name="ord", references=(Reference("custs", "cust", "id", 0.9),))
    with pytest.raises(SimulationError, match=r"ord\.custs: no list of values outside of a key"):
        rows(table, _profile(_CUST), 0)


def test_a_column_of_unmistakable_values_refers_to_its_key_with_all_of_them() -> None:
    made = {value for (value,) in rows(_referring("key", None), _profile(_CUST), 0) if value}
    keys = {value for (_, value) in rows(_CUST, _profile(), 0)}
    assert len(made) == 300
    assert made <= keys, "the same values of the key, drawn again by the same seed"


def test_a_column_of_a_table_refers_to_a_key_of_its_own() -> None:
    table = replace(
        _table(_ranged("id", "bigint", 1000, 1, 1000), _column("prnt", "bigint", 900, 50)),
        references=(Reference("prnt", "t", "id", 1.0),),
    )
    made = rows(table, _profile(table), 0)
    keys = {key for key, _ in made}
    assert {parent for _, parent in made if parent is not None} <= keys, "of the same seed"


@pytest.mark.parametrize(
    ("table", "column"),
    [
        (_keyed(), "pos"),
        (_entities(Entity(("A", "B", "C"), 900, {"kind": 900, "own": 400})), "kind"),
    ],
    ids=["numbered", "discriminator"],
)
def test_a_column_numbered_within_another_or_a_discriminator_that_refers_is_refused(
    table: Table, column: str
) -> None:
    referring = replace(table, references=(Reference(column, "cust", "id", 1.0),))
    with pytest.raises(SimulationError, match=f"t\\.{column}: a column numbered or of a discr"):
        rows(referring, _profile(_CUST), 0)


@pytest.mark.parametrize(
    ("table", "profile", "problem"),
    [
        (_referring(), _profile(), "refers to cust.id, not made"),
        (
            _referring(),
            _profile(replace(_CUST, columns=_CUST.columns[1:])),
            "refers to cust.id, not",
        ),
        (
            _referring(),
            _profile(replace(_CUST, references=(Reference("id", "cust", "key", None),))),
            "refers to a key that refers itself",
        ),
        (_referring(distinct=600), _profile(_CUST), "600 distinct values of 900 rows cannot cover"),
        (
            _referring(coverage=0.5, distinct=400),
            _profile(_CUST),
            "400 distinct values of 900 rows",
        ),
        (_referring("key", 0.9), _profile(_CUST), r"no varchar\(36\) outside of a key of varch"),
        (
            replace(_referring(coverage=0.9), references=(Reference("cust", "cust", "key", 0.9),)),
            _profile(_CUST),
            r"no bigint outside of a key of varchar\(36\) is made",
        ),
    ],
    ids=[
        "no table",
        "no column",
        "a key that refers",
        "more than the key",
        "too few",
        "no number",
        "of no numbers",
    ],
)
def test_a_reference_that_cannot_be_generated_is_refused(
    table: Table, profile: Profile, problem: str
) -> None:
    with pytest.raises(SimulationError, match=f"ord\\.cust: {problem}"):
        rows(table, profile, 0)


# A sentinel of five rows, which is no day.
_NONE = (Value("N/A", 5),)


def test_the_same_seed_gives_the_same_rows() -> None:
    assert rows(_TABLE, _profile(), 7) == rows(_TABLE, _profile(), 7)


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
        rows(_table(column), _profile(), 0)


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
    CURRENCY_CODE: (3, 3, len(CODES)),
    CURRENCY_NUMBER: (3, 3, len(NUMBERS)),
    CURRENCY_NAME: (4, 20, 500),
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
    values = [str(value) for (value,) in rows(_table(column, count=500), _profile(), 0)]
    assert kind.detector.share(values) == 1.0, "every text is of the type, and so is the column"
    assert (min(map(len, values)), max(map(len, values))) == (shortest, longest)


def test_a_column_of_lists_holds_lists_of_the_values_of_its_items_of_its_lengths() -> None:
    column = Column(
        name="v",
        type="varchar(40)",
        statistics=Statistics(0, 200, Lengths(1, 23)),
        list_separator=";",
        items=Findings(Statistics(0, 40, Lengths(1, 2))),
    )
    values = [str(value) for (value,) in rows(_table(column, count=500), _profile(), 0)]
    assert is_list(values, ";", SENTINELS), "lists, some of several numbers"
    assert all(re.fullmatch(r"[0-9]{1,2}(;[0-9]{1,2})*", value) for value in values)
    assert (min(map(len, values)), max(map(len, values))) == (1, 23)
    assert len({item for value in values for item in value.split(";")}) == 40, "its items"


def test_a_column_of_lists_holds_lists_of_values_of_the_type_of_its_items() -> None:
    items = Findings(Statistics(0, 6, Lengths(3, 3)), matches=(Match(CURRENCY_CODE, 1.0),))
    column = Column(
        name="v",
        type="varchar(15)",
        statistics=Statistics(0, 30, Lengths(3, 15)),
        list_separator=";",
        items=items,
    )
    values = [str(value) for (value,) in rows(_table(column, count=100), _profile(), 0)]
    split = [item for value in values for item in value.split(";")]
    assert CURRENCY_CODE.detector.share(split) == 1.0, "codes of currencies"
    assert len(set(split)) == 6


def test_a_discriminator_of_a_column_of_lists_is_refused() -> None:
    column = Column(
        name="v",
        type="varchar(5)",
        statistics=Statistics(0, 2, Lengths(1, 3)),
        list_separator=";",
        items=Findings(Statistics(0, 2, Lengths(1, 1))),
    )
    entities = (Entity(("A",), 5, {"v": 5}), Entity(("B",), 5, {"v": 5}))
    table = replace(_table(column, count=10), discriminator=Discriminator("v", entities))
    with pytest.raises(SimulationError, match=r"t\.v: no discriminator of lists is made"):
        rows(table, _profile(), 0)


def test_a_column_of_lists_without_its_items_is_refused() -> None:
    column = Column(
        name="v", type="varchar(15)", statistics=Statistics(0, 3, Lengths(1, 5)), list_separator=";"
    )
    with pytest.raises(SimulationError, match=r"t\.v: a column of lists without the lengths"):
        rows(_table(column, count=10), _profile(), 0)


def test_a_text_of_a_semantic_type_of_a_project_is_refused(account_number: SemanticType) -> None:
    column = Column(
        name="v",
        type="varchar(11)",
        statistics=Statistics(0, 10, Lengths(11, 11)),
        matches=(Match(account_number, 1.0),),
    )
    with pytest.raises(SimulationError, match=r"t\.v: no account-number is made"):
        rows(_table(column, count=10), _profile(), 0)


def test_a_column_whose_values_fail_the_condition_of_their_type_together_is_refused() -> None:
    column = Column(
        name="v",
        type="varchar(60)",
        statistics=Statistics(0, 10, Lengths(12, 60)),
        matches=(Match(FREE_TEXT, 1.0),),
    )
    with pytest.raises(SimulationError, match=r"t\.v: 10 distinct values of 500 are no free-text"):
        rows(_table(column, count=500), _profile(), 0)


def test_a_text_of_a_semantic_type_that_no_value_has_the_length_of_is_refused() -> None:
    column = Column(
        name="v",
        type="varchar(10)",
        statistics=Statistics(0, 10, Lengths(4, 6)),
        matches=(Match(POSTAL_CODE, 1.0),),
    )
    with pytest.raises(SimulationError, match=r"t\.v: no postal-code of 4 characters can be made"):
        rows(_table(column, count=10), _profile(), 0)
