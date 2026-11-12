"""Tests of the column groups of a table: its columns filled together, in samples made by hand."""

from data_profiler.grouping import group
from data_profiler.profile import Column, ColumnGroup, Statistics, Table, Value
from data_profiler.source import dialect
from data_profiler.workspace import Sample

# The rows of each sample of these tests.
_ROWS = 100


def _filled(first: int, last: int, empty: object = None) -> list[object]:
    """The values of a column filled in the rows from `first` to `last`, `empty` in the others."""
    return ["x" if first <= row <= last else empty for row in range(_ROWS)]


def _groups(
    columns: dict[str, list[object]], sentinels: dict[str, tuple[Value, ...]] | None = None
) -> tuple[ColumnGroup, ...]:
    """The groups of a table of `columns`, whose statistics found `sentinels` of each, by name."""
    found = sentinels or {}
    table = Table(
        name="table",
        rows=_ROWS,
        columns=tuple(
            Column(name, "varchar(10)", Statistics(0, 1, sentinels=found.get(name, ())))
            for name in columns
        ),
    )
    return group(dialect("trino://h/c/s"), table, Sample(columns=columns)).column_groups


def test_columns_filled_in_the_same_rows_are_a_group() -> None:
    assert _groups({"a": _filled(0, 39), "b": _filled(0, 39)}) == (ColumnGroup(("a", "b"), 1.0),)


def test_a_sentinel_of_a_column_is_not_filled_as_a_null_is_not() -> None:
    columns = {"a": _filled(0, 39), "b": _filled(0, 39, "")}
    assert _groups(columns, {"b": (Value("", 60),)}) == (ColumnGroup(("a", "b"), 1.0),)
    assert _groups(columns) == (), "filled where its statistics found no sentinels"


def test_columns_of_a_group_may_miss_a_few_rows_of_one_another() -> None:
    columns = {"a": _filled(0, 39), "b": _filled(0, 37), "c": _filled(2, 39)}
    (found,) = _groups(columns)
    assert found.columns == ("a", "b", "c")
    assert found.coherence == round((38 / 40 + 38 / 40 + 36 / 40) / 3, 3), "the mean of each two"


def test_columns_filled_in_other_rows_are_no_group() -> None:
    assert _groups({"a": _filled(0, 39), "b": _filled(30, 69)}) == ()


def test_columns_filled_in_nearly_every_row_or_in_too_few_take_no_part() -> None:
    assert _groups({"a": _filled(0, 94), "b": _filled(0, 94)}) == (), "filled in 95 of 100 rows"
    assert _groups({"a": _filled(0, 8), "b": _filled(0, 8)}) == (), "filled in 9 rows"
    assert _groups({"a": _filled(0, 89), "b": _filled(0, 89)}) != (), "filled in 90 rows"
    assert _groups({"a": _filled(0, 9), "b": _filled(0, 9)}) != (), "filled in 10 rows"


def test_every_two_columns_of_a_group_are_filled_together_in_nine_of_ten_rows() -> None:
    columns = {"a": _filled(0, 59), "b": _filled(0, 56), "c": _filled(0, 52)}
    assert _groups(columns) == (ColumnGroup(("a", "b"), 0.95),), (
        "c is close to b, at 53 of 57 rows, but not to a, at 53 of 60"
    )


def test_the_groups_are_in_the_order_of_their_first_columns_and_their_columns_in_theirs() -> None:
    columns = {
        "p": _filled(50, 89),
        "a": _filled(0, 39),
        "q": _filled(50, 89),
        "b": _filled(0, 39),
    }
    assert _groups(columns) == (ColumnGroup(("p", "q"), 1.0), ColumnGroup(("a", "b"), 1.0))
