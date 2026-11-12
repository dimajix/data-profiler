"""Tests of columns of lists: found in the sample of a table made by hand, by a separator given."""

from data_profiler.lists import is_listed_with, listed
from data_profiler.profile import Column, Lengths, Statistics, Table, Value
from data_profiler.source import dialect
from data_profiler.workspace import Sample


def _table(*separators: str | None) -> Table:
    """A table of the columns `ids` and `name`, of lists of `separators` or none, in order."""
    ids, name = (*separators, None, None)[:2]
    statistics = Statistics(0, 3, Lengths(1, 7))
    columns = (
        Column("ids", "varchar(40)", statistics, list_separator=ids),
        Column("name", "varchar(40)", statistics, list_separator=name),
    )
    return Table(name="t", rows=3, columns=columns)


# The dialect of the tables of these tests, which tells the sentinels of their samples.
_DIALECT = dialect("trino://h/c/s")

_SAMPLE = Sample({"ids": ["12;47;3", "4", "7;12"], "name": ["Anna", "Otto", "Eva"]})


def _separators(table: Table) -> list[str | None]:
    """The separator of each column of `table`, in order."""
    return [column.list_separator for column in table.columns]


def test_a_column_of_lists_has_the_separator_and_another_has_none() -> None:
    assert _separators(listed(_DIALECT, _table(), _SAMPLE, ";")) == [";", None]


def test_no_column_is_one_of_lists_without_a_separator() -> None:
    assert _separators(listed(_DIALECT, _table(), _SAMPLE, None)) == [None, None]


def test_a_column_of_lists_of_another_separator_than_given_is_none() -> None:
    assert _separators(listed(_DIALECT, _table("|"), _SAMPLE, "|")) == [None, None], (
        "the separator it held is replaced by what the sample shows"
    )


def test_the_nulls_and_the_sentinels_found_of_a_column_are_no_lists() -> None:
    found = Statistics(0, 3, Lengths(0, 7), sentinels=(Value("", 1), Value("N/A", 1)))
    table = Table(name="t", rows=6, columns=(Column("ids", "varchar(40)", found),))
    sample = Sample({"ids": ["12;47;3", None, "", "N/A", "4", "7;12"]})
    (ids,) = listed(_DIALECT, table, sample, ";").columns
    assert ids.list_separator == ";"


def test_a_column_of_no_text_is_no_column_of_lists() -> None:
    table = Table(name="t", rows=2, columns=(Column("price", "decimal(6,2)", Statistics(0, 2)),))
    (price,) = listed(_DIALECT, table, Sample({"price": ["12.50", "3"]}), ".").columns
    assert price.list_separator is None, "a decimal, though its text would be a list of a dot"


def test_a_table_is_listed_with_a_separator_where_no_column_is_a_list_of_another() -> None:
    assert is_listed_with(_table(";"), ";")
    assert is_listed_with(_table(), "|"), "a table of no lists cannot tell"
    assert not is_listed_with(_table(";"), "|")
    assert not is_listed_with(_table(";"), None)
