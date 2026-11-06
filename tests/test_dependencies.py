"""Tests of the column dependencies of tables made by hand.

A table made by hand is counted by a schema that holds its rows, and counts the distinct values of
each expression asked for of them, as the dialect writes it: of the columns it names, in their order
in it, in the rows the first is not null in - nor a sentinel, where the expression leaves its
sentinels aside.
"""

from collections.abc import Mapping, Sequence
from random import Random

from data_profiler.dependencies import determine
from data_profiler.detect import is_filled
from data_profiler.profile import Column, ColumnDependency, Statistics, Table, Value
from data_profiler.source import Source, connect
from data_profiler.workspace import Sample


class _Whole(Source):
    """A schema of one table of `rows`, the values of each column by its name."""

    def __init__(self, table: Table, rows: Mapping[str, Sequence[object]]) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("c", "s", trino.dialect)
        self._table = table
        self._rows = rows
        self.asked: list[list[str]] = []

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        listed = statement.removeprefix("SELECT ").rsplit(" FROM ", 1)[0]
        expressions = _split(listed)
        self.asked.append(expressions)
        return [tuple(self._count(expression) for expression in expressions)]

    def _count(self, expression: str) -> int:
        named = sorted(
            (expression.index(f'"{column.name}"'), column)
            for column in self._table.columns
            if f'"{column.name}"' in expression
        )
        (_, first), *others = named
        values = zip(*(self._rows[column.name] for _, column in named), strict=True)
        # The sentinels left aside where the expression holds those `Dialect.without` writes.
        aside = first.left_aside if "THEN NULL ELSE" in expression else frozenset()
        filled = (found for found in values if is_filled(found[0], aside))
        return len(set(filled)) if others else len({found[0] for found in filled})

    def close(self) -> None:
        pass


def _split(listed: str) -> list[str]:
    """The expressions of `listed`, split at the commas outside of parentheses."""
    expressions, depth, start = [], 0, 0
    for place, character in enumerate(listed):
        depth += {"(": 1, ")": -1}.get(character, 0)
        if character == "," and depth == 0:
            expressions.append(listed[start:place].strip())
            start = place + 1
    return [*expressions, listed[start:].strip()]


def _column(name: str, kind: str = "bigint", sentinels: Sequence[str] = ()) -> Column:
    found = tuple(Value(sentinel, 1) for sentinel in sentinels)
    return Column(name, kind, Statistics(0, 10, sentinels=found))


def _determined(
    rows: Mapping[str, Sequence[object]],
    whole: Mapping[str, Sequence[object]] | None = None,
    columns: Sequence[Column] = (),
) -> tuple[tuple[ColumnDependency, ...], _Whole]:
    """The dependencies of a table of `rows` in its sample, and of `whole` on the table."""
    given = {column.name: column for column in columns}
    made = tuple(given.get(name) or _column(name) for name in rows)
    table = Table(name="t", rows=len(next(iter(rows.values()))), columns=made)
    source = _Whole(table, whole or rows)
    sample = Sample(columns={name: list(values) for name, values in rows.items()})
    return determine(source, table, sample).column_dependencies, source


# A determinant of ten values, each in ten rows, and a column that follows from it.
_OF = [row % 10 for row in range(100)]
_HALF = [value // 2 for value in _OF]


def test_a_column_whose_values_follow_from_another_is_a_dependent_of_it() -> None:
    found, _ = _determined({"a": _OF, "b": _HALF, "c": [row % 7 for row in range(100)]})
    assert found == (ColumnDependency(("a",), ("b",), 1.0),)


def test_columns_that_follow_from_each_other_are_equivalent_determinants() -> None:
    named = [f"n{value}" for value in _OF]
    found, _ = _determined({"code": _OF, "half": _HALF, "name": named})
    assert found == (ColumnDependency(("code", "name"), ("half",), 1.0),)


def test_columns_that_follow_from_each_other_alone_are_a_dependency_of_no_dependent() -> None:
    found, _ = _determined({"code": _OF, "name": [f"n{value}" for value in _OF]})
    assert found == (ColumnDependency(("code", "name"), (), 1.0),)


def test_a_column_of_values_each_of_one_row_is_neither_determinant_nor_dependent() -> None:
    found, _ = _determined({"a": _OF, "b": _HALF, "id": list(range(100))})
    assert found == (ColumnDependency(("a",), ("b",), 1.0),)


def test_no_query_is_sent_where_no_dependency_is_found() -> None:
    found, source = _determined({"a": _OF, "b": [row % 7 for row in range(100)]})
    assert (found, source.asked) == ((), [])


def test_a_determinant_of_values_that_mostly_do_not_repeat_takes_no_part() -> None:
    # Of 100 rows, 40 of 20 values twice each, and 60 of a value each.
    rare = [row // 2 if row < 40 else row for row in range(100)]
    found, _ = _determined({"a": rare, "b": [value % 3 for value in rare]})
    assert found == ()


def test_a_column_constant_in_the_rows_of_a_determinant_does_not_follow_from_it() -> None:
    # Of two entities, each column filled in the rows of one alone.
    first = [value if row < 50 else None for row, value in enumerate(_OF)]
    second = [None if row < 50 else value for row, value in enumerate(_OF)]
    found, _ = _determined({"a": first, "b": second})
    assert found == ()


def test_a_column_of_nearly_one_value_in_the_rows_of_a_determinant_does_not_follow() -> None:
    flag = [0 if row == 0 else 1 for row in range(100)]
    sparse = [1 if row == 0 else None for row in range(100)]
    found, _ = _determined({"a": _OF, "flag": flag, "sparse": sparse})
    assert found == (), "a constant departs no more"


def test_the_sentinels_of_a_determinant_are_aside_and_a_null_of_a_dependent_a_value() -> None:
    # The sentinel in the first row of each ten, each with another value of the others.
    of = ["" if row % 10 == 0 else str(row % 10) for row in range(100)]
    nulls = [
        row if not text else None if text in "12" else int(text) // 2 for row, text in enumerate(of)
    ]
    # Of the rows of 3, one null, the others not.
    mixed = [
        row % 3 if not text else None if row == 13 else int(text) // 3
        for row, text in enumerate(of)
    ]
    found, _ = _determined(
        {"a": of, "b": nulls, "c": mixed}, columns=[_column("a", "varchar(2)", sentinels=[""])]
    )
    assert found == (ColumnDependency(("a",), ("b",), 1.0),)


def test_a_dependency_of_few_rows_departing_in_the_sample_holds_as_strictly_as_on_table() -> None:
    # Of 400 rows, 40 values of ten rows each.
    of = [row % 40 for row in range(400)]
    one = [value // 2 if row else -1 for row, value in enumerate(of)]
    found, _ = _determined({"a": of, "b": one})
    assert found == (ColumnDependency(("a",), ("b",), 0.975),), (
        "one row of 400 departs, of one value of 40, which comes with two"
    )
    five = [value // 2 if row >= 5 else -1 for row, value in enumerate(of)]
    assert _determined({"a": of, "b": five})[0] == (), "five rows of 400 depart in the sample"


def test_of_a_dependency_that_falls_short_on_the_table_the_dependents_that_hold_are_kept() -> None:
    sample = {"a": _OF, "b": _HALF, "c": [value % 3 for value in _OF], "d": [v * 3 for v in _OF]}
    # On the table, `c` departs: its value of each value of `a` differs in the last row of it.
    whole = {**sample, "c": [*sample["c"][:-10], *(value + 1 for value in sample["c"][-10:])]}
    found, source = _determined(sample, whole)
    assert found == (ColumnDependency(("a", "d"), ("b",), 1.0),)
    together, alone, again = source.asked
    assert len(together) == 4, "the determinant alone, with all others, and the equivalent with it"
    assert len(alone) == 3, "each of the others alone"
    assert len(again) == 1, "those that pass together again"


def test_an_equivalent_that_does_not_determine_the_first_on_the_table_is_a_dependent() -> None:
    named = [f"n{value}" for value in _OF]
    codes = [value if row < 90 else value + 10 for row, value in enumerate(_OF)]
    sample: dict[str, Sequence[object]] = {"code": _OF, "name": named}
    whole = {**sample, "code": codes}
    found, _ = _determined(sample, whole)
    assert found == (ColumnDependency(("code",), ("name",), 1.0),), (
        "each code of one name, and each name of two codes"
    )


def test_the_dependencies_of_the_most_columns_that_follow_are_verified_of_too_many() -> None:
    rows: dict[str, Sequence[object]] = {}
    for index in range(51):
        random = Random(index)
        values = [random.randrange(10) for _ in range(100)]
        rows[f"d{index}"] = values
        rows[f"e{index}"] = [value // 2 for value in values]
    rows["most"] = _OF
    rows["half"], rows["third"] = _HALF, [value // 3 for value in _OF]
    found, _ = _determined(rows)
    assert len(found) == 50
    assert ColumnDependency(("most",), ("half", "third"), 1.0) in found
