"""Tests of the entities of tables: of tables made by hand, and against the simulation environment.

The tests of tables made by hand count them by a schema that answers the query of `entities` with
the counts given of each value; those against the simulation environment need it to run.
"""

from collections.abc import Mapping
from dataclasses import replace

from data_profiler.entities import discriminate
from data_profiler.profile import Column, Discriminator, Entity, Profile, Statistics, Table, Value
from data_profiler.source import Source, connect

# The columns of each table made by hand, besides the candidates: `a` to `f`.
_OTHERS = ("a", "b", "c", "d", "e", "f")

# Of each value of a candidate, its rows and the rows each of `_OTHERS` is filled in, in order.
type _Given = Mapping[str, tuple[int, tuple[int, ...]]]


class _Counted(Source):
    """A schema of one table, which counts the values of its candidates as `given`."""

    def __init__(self, given: Mapping[str, _Given]) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("c", "s", trino.dialect)
        self._given = given

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        # Grouped by each candidate: its values, their groupings, the rows and the nulls of each
        # column of the table, the candidates first, which are filled in every row.
        names = list(self._given)
        rows: list[tuple[object, ...]] = []
        for index, name in enumerate(names):
            for value, (count, filled) in self._given[name].items():
                values = [value if place == index else None for place in range(len(names))]
                groupings = [0 if place == index else 1 for place in range(len(names))]
                nulls = [0] * len(names) + [count - rows_filled for rows_filled in filled]
                rows.append((*values, *groupings, count, *nulls))
        return rows

    def close(self) -> None:
        pass


def _found(given: Mapping[str, _Given]) -> Discriminator | None:
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
    return discriminate(_Counted(given), table).discriminator


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


def _partners(example: Profile) -> Table:
    """The table of the business partners of the example, as it was made, without its entities."""
    (table,) = [table for table in example.tables if table.name == "prtnr"]
    return replace(table, discriminator=None)


def test_the_entities_of_a_table_are_told_apart_by_the_values_of_its_discriminator(
    source: Source, example: Profile
) -> None:
    (made,) = [table for table in example.tables if table.name == "prtnr"]
    found = discriminate(source, _partners(example)).discriminator
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
    assert discriminate(source, replace(table, columns=columns)).discriminator is None


def test_the_rows_of_a_value_the_profile_does_not_hold_are_of_no_entity(
    source: Source, example: Profile
) -> None:
    table = _partners(example)
    columns = tuple(
        replace(column, values=tuple(value for value in column.values if value.value != "M"))
        for column in table.columns
    )
    found = discriminate(source, replace(table, columns=columns)).discriminator
    assert found is not None
    assert [entity.values for entity in found.entities] == [("K", "KX"), ("L", "LX"), ("I",)]
    assert sum(entity.rows for entity in found.entities) == table.rows - 800
