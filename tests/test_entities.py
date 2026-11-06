"""Tests of the entities of tables: of tables made by hand, and against the simulation environment.

The tests of tables made by hand count them by a schema that answers the groups `entities` asks for
with the counts given of each value; those against the simulation environment need it to run.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace

import pytest

from data_profiler.entities import discriminate
from data_profiler.overrides import DiscriminatorOverride, EntityOverride, GivenDiscriminator
from data_profiler.profile import (
    Column,
    Discriminator,
    Entity,
    Findings,
    Profile,
    Statistics,
    Table,
    Value,
)
from data_profiler.source import Source, connect

# The columns of each table made by hand, besides the candidates: `a` to `f`.
_OTHERS = ("a", "b", "c", "d", "e", "f")

# Of each value of a candidate, its rows and the rows each of `_OTHERS` is filled in, in order.
type _Given = Mapping[str, tuple[int, tuple[int, ...]]]


class _Counted(Source):
    """A schema of one table, which counts the values of its candidates as `given`.

    The values of the lists of a column it counts as `lists` gives them, by the column.
    """

    def __init__(
        self, given: Mapping[str, _Given], lists: Mapping[str, _Given] | None = None
    ) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("c", "s", trino.dialect)
        self._given = given
        self._lists = lists or {}

    def unnested(self, table: str, column: str, separator: str) -> Source:
        return _Counted({**self._given, column: self._lists[column]})

    def grouped(
        self, table: str, columns: Sequence[str], expressions: Sequence[str], step: str
    ) -> list[tuple[int, object, tuple[object, ...]]]:
        # Of each value of each column grouped by, the rows and the nulls of each column of the
        # table, the candidates first, filled in every row.
        groups: list[tuple[int, object, tuple[object, ...]]] = []
        for index, name in enumerate(columns):
            for value, (count, filled) in self._given[name].items():
                nulls = [0] * len(self._given) + [count - rows_filled for rows_filled in filled]
                groups.append((index, value, (count, *nulls)))
        return groups

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        raise AssertionError("the entities are counted by their groups alone")

    def close(self) -> None:
        pass


def _found(
    given: Mapping[str, _Given], overridden: GivenDiscriminator = None
) -> Discriminator | None:
    """The discriminator of a table of the candidates `given` and `_OTHERS`, as they are counted."""
    candidates = tuple(
        Column(
            name,
            "varchar(2)",
            Statistics(0, len(values)),
            values=tuple(
                Value(value, count)
                for value, (count, _) in sorted(values.items(), key=lambda v: -v[1][0])
            ),
        )
        for name, values in given.items()
    )
    others = tuple(Column(name, "varchar(5)", Statistics(0, 1)) for name in _OTHERS)
    rows = sum(count for count, _ in next(iter(given.values())).values())
    table = Table(name="t", rows=rows, columns=(*candidates, *others))
    return discriminate(_Counted(given), table, overridden).discriminator


def _values(found: Discriminator | None) -> list[tuple[str, ...]]:
    """The values of each entity of `found`, none where it is None."""
    return [] if found is None else [entity.values for entity in found.entities]


def test_values_told_apart_by_three_columns_are_two_entities() -> None:
    found = _found(
        {"kind": {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (50, (0, 0, 0, 50, 50, 0))}}
    )
    assert found is not None
    assert found.column == "kind"
    assert found.entities == (
        Entity(("A",), 100, {"kind": 100, "a": 100, "b": 100, "c": 100, "d": 0, "e": 0, "f": 0}),
        Entity(("B",), 50, {"kind": 50, "a": 0, "b": 0, "c": 0, "d": 50, "e": 50, "f": 0}),
    ), "each with the rows each column is filled in, the one of more rows first"


def _of_lists(lists: _Given, texts: _Given) -> Table:
    """A table of a column of lists `kinds`, whose texts are `texts` and their values `lists`."""
    column = Column(
        "kinds",
        "varchar(5)",
        Statistics(0, len(texts)),
        list_separator=";",
        items=Findings(
            Statistics(0, len(lists)),
            values=tuple(Value(value, count) for value, (count, _) in lists.items()),
        ),
        values=tuple(Value(text, count) for text, (count, _) in texts.items()),
    )
    others = tuple(Column(name, "varchar(5)", Statistics(0, 1)) for name in _OTHERS)
    return Table(name="t", rows=150, columns=(column, *others))


def test_the_values_of_the_lists_of_a_column_are_a_candidate_of_a_discriminator() -> None:
    lists = {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (60, (0, 0, 0, 60, 60, 0))}
    texts = {"A": (90, (90, 90, 90, 0, 0, 0)), "A;B": (10, (10, 10, 10, 10, 10, 0))}
    table = _of_lists(lists, texts)
    found = discriminate(_Counted({"kinds": texts}, {"kinds": lists}), table, None).discriminator
    assert found is not None
    assert found.column == "kinds"
    assert [entity.values for entity in found.entities] == [("A",), ("B",)], "not its texts"
    assert found.rows == 160, "a row of each entity a value of its list is of, more than the table"


def test_of_a_candidate_of_lists_and_another_the_one_of_more_columns_telling_apart_wins() -> None:
    lists = {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (60, (0, 0, 0, 60, 60, 60))}
    texts = {"A": (90, (90, 90, 90, 0, 0, 0)), "A;B": (10, (10, 10, 10, 10, 10, 10))}
    table = _of_lists(lists, texts)
    status = Column(
        "status", "varchar(2)", Statistics(0, 2), values=(Value("X", 90), Value("Y", 60))
    )
    statuses = {"X": (90, (90, 90, 0, 0, 0, 0)), "Y": (60, (0, 0, 60, 60, 0, 0))}
    kinds, *others = table.columns
    table = replace(table, columns=(kinds, status, *others))
    counted = _Counted({"kinds": texts, "status": statuses}, {"kinds": lists})
    found = discriminate(counted, table, None).discriminator
    assert found is not None
    assert found.column == "kinds", "of six columns telling apart, not of four"


def test_a_discriminator_given_of_a_column_of_lists_is_of_the_values_of_its_lists() -> None:
    lists = {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (60, (0, 0, 0, 60, 60, 0))}
    texts = {"A": (90, (90, 90, 90, 0, 0, 0)), "A;B": (10, (10, 10, 10, 10, 10, 0))}
    given = DiscriminatorOverride("kinds", {"b": EntityOverride(("B",))})
    counted = _Counted({"kinds": texts}, {"kinds": lists})
    found = discriminate(counted, _of_lists(lists, texts), given).discriminator
    assert found is not None
    assert _values(found) == [("A",), ("B",)], "of the values of its lists, the most rows first"
    assert found.given == (("B",),), "counted with the values given"


def test_values_told_apart_by_fewer_than_three_columns_are_one_entity() -> None:
    given = {"status": {"open": (100, (100, 100, 0, 0, 0, 0)), "done": (50, (0, 0, 0, 0, 0, 0))}}
    assert _found(given) is None, "a status whose one value fills two columns of its own"


def test_a_column_tells_values_apart_from_nine_of_ten_rows_filled_and_one_of_ten() -> None:
    edge = {"A": (100, (90, 90, 90, 0, 0, 0)), "B": (100, (10, 10, 10, 0, 0, 0))}
    assert _values(_found({"kind": edge})) == [("A",), ("B",)]
    within = {"A": (100, (89, 90, 90, 0, 0, 0)), "B": (100, (10, 10, 11, 0, 0, 0))}
    assert _found({"kind": within}) is None, "only one of the three columns tells them apart"


def test_a_value_of_too_few_rows_joins_the_entity_it_is_closest_to() -> None:
    given = {
        "kind": {
            "A": (100, (100, 100, 100, 0, 0, 0)),
            "B": (80, (0, 0, 0, 80, 80, 80)),
            "C": (9, (0, 0, 0, 9, 9, 0)),
        }
    }
    assert _values(_found(given)) == [("A",), ("B", "C")], "not the first, nor one of its own"


def test_a_value_of_ten_rows_is_told_apart_as_any_other() -> None:
    given = {
        "kind": {
            "A": (100, (100, 100, 100, 0, 0, 0)),
            "B": (80, (0, 0, 0, 80, 80, 80)),
            "C": (10, (10, 10, 10, 10, 10, 10)),
        }
    }
    assert _values(_found(given)) == [("A",), ("B",), ("C",)]


def test_of_several_candidates_the_one_whose_entities_the_most_columns_tell_apart_wins() -> None:
    three = {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (100, (0, 0, 0, 0, 0, 0))}
    four = {"X": (100, (100, 100, 100, 100, 0, 0)), "Y": (100, (0, 0, 0, 0, 0, 0))}
    found = _found({"one": three, "two": four})
    assert found is not None
    assert found.column == "two", "four columns tell its entities apart, three those of the other"


def test_of_candidates_alike_the_one_of_fewer_entities_wins_then_the_first() -> None:
    two = {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (100, (0, 0, 0, 100, 100, 100))}
    three = {
        "X": (100, (100, 100, 100, 0, 0, 0)),
        "Y": (50, (0, 0, 0, 50, 50, 50)),
        "Z": (50, (0, 0, 0, 0, 0, 0)),
    }
    found = _found({"three": three, "two": two})
    assert found is not None
    assert found.column == "two", "six columns tell the entities of either apart"
    found = _found({"first": two, "second": two})
    assert found is not None
    assert found.column == "first"


def _given(column: str, **entities: tuple[str, ...]) -> DiscriminatorOverride:
    """The discriminator `column` given by hand, of entities of the values given by their names."""
    given = {name: EntityOverride(values) for name, values in entities.items()}
    return DiscriminatorOverride(column, given)


def test_the_entities_given_are_taken_whether_or_not_columns_tell_them_apart() -> None:
    given = {
        "kind": {
            "A": (100, (100, 100, 100, 0, 0, 0)),
            "B": (80, (100, 100, 100, 0, 0, 0)),
            "C": (60, (0, 0, 0, 60, 60, 60)),
        }
    }
    assert _values(_found(given)) == [("A", "B"), ("C",)], "as found"
    found = _found(given, _given("kind", a=("A",), b=("B",)))
    assert _values(found) == [("A",), ("B",), ("C",)]
    assert found is not None
    assert found.given == (("A",), ("B",)), "the values given it was counted with"


def test_the_values_not_given_join_the_entities_given_or_each_other_as_found() -> None:
    given = {
        "kind": {
            "A": (100, (100, 100, 100, 0, 0, 0)),
            "B": (80, (0, 0, 0, 80, 80, 80)),
            "C": (60, (60, 60, 60, 0, 0, 0)),
            "D": (40, (0, 0, 0, 40, 40, 40)),
            "E": (5, (0, 0, 0, 5, 5, 5)),
        }
    }
    found = _found(given, _given("kind", b=("B",)))
    assert _values(found) == [("A", "C"), ("B", "D", "E")], "the one of most rows first"


def test_a_value_given_of_too_few_rows_is_not_compared() -> None:
    given = {
        "kind": {
            "A": (100, (100, 100, 100, 0, 0, 0)),
            "B": (80, (0, 0, 0, 80, 80, 80)),
            "C": (5, (5, 5, 5, 0, 0, 0)),
        }
    }
    found = _found(given, _given("kind", c=("C",)))
    assert _values(found) == [("A",), ("B",), ("C",)], (
        "A joins no entity of no value of enough rows"
    )


def test_a_discriminator_given_is_taken_though_it_tells_one_entity_and_another_column_more() -> (
    None
):
    one = {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (100, (100, 100, 100, 0, 0, 0))}
    two = {"X": (100, (100, 100, 100, 0, 0, 0)), "Y": (100, (0, 0, 0, 100, 100, 100))}
    found = _found({"one": one, "two": two}, _given("one"))
    assert found is not None
    assert (found.column, _values(found)) == ("one", [("A", "B")])


def test_the_values_given_the_profile_does_not_hold_are_left_out_warning_of_them(
    caplog: pytest.LogCaptureFixture,
) -> None:
    given = {"kind": {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (50, (0, 0, 0, 50, 50, 0))}}
    found = _found(given, _given("kind", a=("A", "X"), b=("B",), y=("Y",)))
    assert _values(found) == [("A",), ("B",)]
    assert found is not None
    assert found.given == (("A", "X"), ("B",), ("Y",)), "as given, of all environments"
    assert (
        "The overrides give entities of t values the profile does not hold of kind, which are left"
        " out: a, y"
    ) in caplog.messages


def test_a_discriminator_given_of_a_column_of_no_values_held_has_no_entities_warning_of_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    given = {"kind": {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (50, (0, 0, 0, 50, 50, 0))}}
    found = _found(given, _given("a", a=("A",)))
    assert found == Discriminator("a", (), (("A",),)), "counted with the values given"
    assert (
        "The overrides give the discriminator of t as a, of which the profile holds no values: it"
        " has no entities"
    ) in caplog.messages


def test_a_table_given_no_discriminator_has_none_whatever_is_found() -> None:
    given = {"kind": {"A": (100, (100, 100, 100, 0, 0, 0)), "B": (50, (0, 0, 0, 50, 50, 0))}}
    assert _found(given, False) is None


def _partners(example: Profile) -> Table:
    """The table of the business partners of the example, as it was made, without its entities."""
    (table,) = [table for table in example.tables if table.name == "prtnr"]
    return replace(table, discriminator=None)


def test_the_entities_of_a_table_are_told_apart_by_the_values_of_its_discriminator(
    source: Source, example: Profile
) -> None:
    (made,) = [table for table in example.tables if table.name == "prtnr"]
    found = discriminate(source, _partners(example), None).discriminator
    assert found == made.discriminator, "the entities it was made with, counted on the table"
    assert found is not None
    assert [entity.values for entity in found.entities] == [
        ("K", "KX"),
        ("L", "LX"),
        ("I",),
        ("M",),
    ], "values filling the same columns are one entity, and one of few rows joins the closest"


def test_a_column_whose_values_the_profile_does_not_hold_tells_no_entities_apart(
    source: Source, example: Profile
) -> None:
    table = _partners(example)
    columns = tuple(replace(column, values=()) for column in table.columns)
    assert discriminate(source, replace(table, columns=columns), None).discriminator is None


def test_the_rows_of_a_value_the_profile_does_not_hold_are_of_no_entity(
    source: Source, example: Profile
) -> None:
    table = _partners(example)
    columns = tuple(
        replace(column, values=tuple(value for value in column.values if value.value != "M"))
        for column in table.columns
    )
    found = discriminate(source, replace(table, columns=columns), None).discriminator
    assert found is not None
    assert [entity.values for entity in found.entities] == [("K", "KX"), ("L", "LX"), ("I",)]
    assert sum(entity.rows for entity in found.entities) == table.rows - 800


def test_the_entities_given_of_a_table_are_counted_on_it_beside_those_found(
    source: Source, example: Profile
) -> None:
    given = _given("prtnr_typ_cd", customer=("K",), other=("KX",), supplier=("L",))
    found = discriminate(source, _partners(example), given).discriminator
    assert found is not None
    assert [entity.values for entity in found.entities] == [
        ("K",),
        ("L", "LX"),
        ("I",),
        ("M",),
        ("KX",),
    ], "KX apart, as given, and LX joining the entity given that it is closest to"
    assert found.given == (("K",), ("KX",), ("L",))
    (made,) = [table for table in example.tables if table.name == "prtnr"]
    assert made.discriminator is not None
    assert found.entities[1] == made.discriminator.entities[1], "counted as found"
