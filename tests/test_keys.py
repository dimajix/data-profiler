"""Tests of the keys of tables: of tables made by hand, and against the simulation environment.

The tests of tables made by hand count them by a schema that answers, of each candidate of a
table, as many distinct values as rows, but of those it is given, and keeps the candidates it was
asked of, as the expressions of the dialect name them; those against the simulation environment need
it to run.
"""

from collections.abc import Collection, Sequence
from itertools import combinations

import pytest

from data_profiler.keys import identify
from data_profiler.profile import Column, PrimaryKey, Profile, Statistics, Table, Value
from data_profiler.sampling import take
from data_profiler.source import Source, connect
from data_profiler.workspace import Sample


class _Counted(Source):
    """A schema of `table`, whose candidates of `duplicated` have values of more than one row."""

    def __init__(self, table: Table, duplicated: Collection[tuple[str, ...]] = ()) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("c", "s", trino.dialect)
        names = [column.name for column in table.columns]
        # Of one column, of two and of three, as the overrides may give a key of more.
        self._candidates = [found for size in (1, 2, 3) for found in combinations(names, size)]
        self._rows = table.rows
        self._duplicated = duplicated
        self.asked: list[list[tuple[str, ...]]] = []

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        # The candidates whose counts the statement holds, in their order in it.
        held = sorted(
            (statement.index(self.dialect.exactly_distinct(found)), found)
            for found in self._candidates
            if self.dialect.exactly_distinct(found) in statement
        )
        asked = [found for _, found in held]
        self.asked.append(asked)
        counts = (self._rows - 1 if found in self._duplicated else self._rows for found in asked)
        return [(self._rows, *counts)]

    def close(self) -> None:
        pass


def _column(
    name: str, distinct: int, kind: str = "bigint", nulls: int = 0, sentinels: int = 0
) -> Column:
    """A column `name` of the type `kind`, of `distinct` values counted, `nulls` and sentinels."""
    found = (Value("", sentinels),) if sentinels else ()
    return Column(name, kind, Statistics(nulls, distinct, sentinels=found))


def _table(rows: int, *columns: Column) -> Table:
    return Table(name="t", rows=rows, columns=columns)


def _sample(**columns: Sequence[object]) -> Sample:
    return Sample(columns={name: list(values) for name, values in columns.items()})


def test_a_column_of_values_each_of_one_row_is_a_key_and_the_primary_one() -> None:
    table = _table(100, _column("id", 99), _column("kind", 3))
    source = _Counted(table)
    found = identify(source, table, _sample(id=[1, 2, 3], kind=[1, 1, 2]), None)
    assert found.keys == (("id",),)
    assert found.primary_key == PrimaryKey(("id",))
    assert source.asked == [[("id",)]], "a column of few values no candidate, nor a pair with a key"


def test_only_a_column_its_statistics_and_its_sample_indicate_is_verified() -> None:
    table = _table(
        100,
        _column("few", 97),
        _column("nulls", 100, nulls=1),
        _column("double", 100, "double"),
        _column("moment", 100, "timestamp(3)"),
        _column("sentinels", 100, sentinels=1),
        _column("twice", 100),
    )
    source = _Counted(table)
    sample = _sample(
        few=[1, 2], nulls=[1, 2], double=[1.0, 2.0], moment=[1, 2], sentinels=[1, 2], twice=[1, 1]
    )
    found = identify(source, table, sample, None)
    assert (found.keys, found.primary_key) == ((), None)
    assert source.asked == [], "no query of no candidate"


def test_a_candidate_of_values_of_more_than_one_row_in_the_table_is_no_key() -> None:
    table = _table(100, _column("id", 100))
    found = identify(_Counted(table, {("id",)}), table, _sample(id=[1, 2]), None)
    assert found.keys == ()


def test_two_columns_whose_values_the_sample_shows_twice_are_a_key_where_unique_together() -> None:
    table = _table(100, _column("ord", 50), _column("pos", 2), _column("qty", 3))
    source = _Counted(table)
    sample = _sample(ord=[1, 1, 2, 2], pos=[1, 2, 1, 2], qty=[1, 2, 2, 1])
    found = identify(source, table, sample, None)
    assert found.keys == (("ord", "pos"), ("ord", "qty"))
    assert source.asked == [[("ord", "pos"), ("ord", "qty")]], (
        "the product of their distinct values reaching the rows, the closest first"
    )
    assert found.primary_key == PrimaryKey(("ord", "pos")), "the first in the table"


def test_no_pair_is_tried_of_a_key_or_of_a_column_unique_in_the_sample() -> None:
    table = _table(100, _column("id", 100), _column("near", 99), _column("kind", 50))
    source = _Counted(table, {("near",)})
    sample = _sample(id=[1, 2, 3], near=[1, 2, 3], kind=[1, 1, 2])
    found = identify(source, table, sample, None)
    assert found.keys == (("id",),)
    assert source.asked == [[("id",), ("near",)]], "the sample shows nothing a pair tells apart"


def test_the_ten_pairs_closest_to_the_rows_are_verified() -> None:
    columns = [_column(f"c{place:02}", 10 + place) for place in range(12)]
    table = _table(100, *columns)
    source = _Counted(table)
    # Each column of values twice, those of the first in other rows than those of the others.
    sample = _sample(**{c.name: [0, 1, 0, 1] for c in columns[1:]}, c00=[0, 0, 1, 1])
    found = identify(source, table, sample, None)
    (asked,) = source.asked
    assert len(asked) == 10
    assert asked[0] == ("c00", "c01"), "the smallest product of distinct values first"
    assert all("c00" in pair for pair in asked), "the only pairs unique in the sample"
    assert len(found.keys) == 10


def test_of_several_keys_the_primary_is_of_whole_numbers_before_the_first() -> None:
    table = _table(100, _column("code", 100, "varchar(8)"), _column("id", 100))
    found = identify(_Counted(table), table, _sample(code=["a", "b"], id=[1, 2]), None)
    assert found.keys == (("code",), ("id",))
    assert found.primary_key == PrimaryKey(("id",))


def test_more_candidates_than_ten_are_verified_in_several_queries() -> None:
    columns = [_column(f"c{place:02}", 100) for place in range(12)]
    table = _table(100, *columns)
    source = _Counted(table)
    found = identify(source, table, _sample(**{column.name: [1, 2] for column in columns}), None)
    assert [len(asked) for asked in source.asked] == [10, 2]
    assert len(found.keys) == 12


def test_a_key_of_one_column_is_the_primary_before_one_of_two_of_whole_numbers() -> None:
    table = _table(100, _column("code", 100, "varchar(8)"), _column("ord", 50), _column("pos", 2))
    sample = _sample(code=["a", "b", "c", "d"], ord=[1, 1, 2, 2], pos=[1, 2, 1, 2])
    found = identify(_Counted(table), table, sample, None)
    assert found.keys == (("code",), ("ord", "pos"))
    assert found.primary_key == PrimaryKey(("code",))


def test_a_primary_key_given_is_verified_with_the_candidates_and_is_the_primary() -> None:
    table = _table(100, _column("id", 100), _column("ord", 50), _column("pos", 2))
    source = _Counted(table)
    sample = _sample(id=[1, 2, 3, 4], ord=[1, 1, 2, 2], pos=[1, 2, 1, 2])
    found = identify(source, table, sample, ("pos", "ord"))
    assert found.primary_key == PrimaryKey(("ord", "pos"), given=True), "in the order of the table"
    assert found.keys == (("id",), ("ord", "pos"))
    assert source.asked == [[("id",), ("ord", "pos")]], "a candidate already"


def test_a_primary_key_given_that_is_no_candidate_is_verified_beside_them() -> None:
    table = _table(100, _column("id", 100), _column("ord", 50), _column("qty", 1))
    source = _Counted(table)
    found = identify(source, table, _sample(id=[1, 2], ord=[1, 1], qty=[1, 1]), ("ord", "qty"))
    assert source.asked == [[("id",), ("ord", "qty")]]
    assert found.keys == (("id",), ("ord", "qty")), "unique, and of no key of fewer columns"
    assert found.primary_key == PrimaryKey(("ord", "qty"), given=True)


def test_a_primary_key_given_of_more_columns_or_of_nulls_is_none_of_the_keys() -> None:
    table = _table(
        100, _column("a", 50), _column("b", 2), _column("c", 3), _column("n", 9, nulls=1)
    )
    sample = _sample(a=[1, 1], b=[1, 2], c=[1, 1], n=[1, 2])
    found = identify(_Counted(table), table, sample, ("a", "b", "c"))
    assert ("a", "b", "c") not in found.keys, "a key is of two columns at most"
    found = identify(_Counted(table), table, sample, ("a", "n"))
    assert ("a", "n") not in found.keys, "the columns of a key have no nulls"
    assert found.primary_key == PrimaryKey(("a", "n"), given=True)


def test_a_primary_key_given_of_a_key_of_fewer_columns_is_none_of_the_keys() -> None:
    table = _table(100, _column("id", 100), _column("ord", 50))
    found = identify(_Counted(table), table, _sample(id=[1, 2], ord=[1, 1]), ("id", "ord"))
    assert found.keys == (("id",),)
    assert found.primary_key == PrimaryKey(("id", "ord"), given=True)


def test_a_primary_key_given_whose_values_are_not_unique_is_warned_of_and_kept(
    caplog: pytest.LogCaptureFixture,
) -> None:
    table = _table(100, _column("ord", 50), _column("qty", 1))
    source = _Counted(table, {("ord", "qty")})
    found = identify(source, table, _sample(ord=[1, 1], qty=[1, 1]), ("ord", "qty"))
    assert found.keys == ()
    assert found.primary_key == PrimaryKey(("ord", "qty"), given=True)
    assert caplog.messages[0] == (
        "The overrides give the primary key of t as ord, qty, whose values are not unique"
    )


def test_a_table_of_no_rows_has_no_keys() -> None:
    table = _table(0, _column("id", 0))
    source = _Counted(table)
    found = identify(source, table, _sample(id=[]), None)
    assert (found.keys, found.primary_key, source.asked) == ((), None, [])


def test_the_keys_of_a_table_are_verified_on_the_whole_table(
    source: Source, example: Profile
) -> None:
    (made,) = [table for table in example.tables if table.name == "ord_itm"]
    table = Table(name=made.name, rows=made.rows, columns=made.columns)
    found = identify(source, table, take(source, table), None)
    assert set(made.keys) <= set(found.keys), "those it was made with, among those it has"
    assert ("ord_id", "pos_no") in found.keys
    assert found.primary_key == made.primary_key
