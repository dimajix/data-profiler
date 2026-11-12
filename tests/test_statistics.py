"""Tests of the statistics of a table, against the simulation environment, which has to run."""

import re

import pytest

from data_profiler.profile import Lengths, Range, Value
from data_profiler.source import Source, SourceError, connect
from data_profiler.statistics import count


def test_only_a_column_of_texts_has_its_lengths_counted(source: Source) -> None:
    counted = {column.name: column.statistics for column in count(source, "cust", {}).columns}
    assert counted["cust_nm"].lengths is not None
    assert counted["crt_dt"].lengths is None
    assert counted["crdt_lmt_amt"].lengths is None


def test_the_range_of_a_column_whose_values_have_an_order_is_counted_as_text(
    source: Source,
) -> None:
    counted = {column.name: column.statistics for column in count(source, "cust", {}).columns}
    assert counted["actv_flg"].range == Range("false", "true")
    for name in ("cust_id", "cust_nm", "crt_dt", "upd_ts", "crdt_lmt_amt"):
        assert counted[name].range is not None, name


def test_the_range_of_a_column_is_of_the_texts_the_database_writes_of_all_their_digits(
    source: Source,
) -> None:
    counted = {column.name: column.statistics for column in count(source, "cust", {}).columns}
    moments = counted["upd_ts"].range
    assert moments is not None
    for end in (moments.smallest, moments.largest):
        assert end is not None
        assert re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}", end
        ), "a moment of the precision of its type, `timestamp(3)`"


def test_a_table_that_does_not_exist_is_not_counted(source: Source) -> None:
    with pytest.raises(SourceError, match="has no table nowhere"):
        count(source, "nowhere", {})


def test_the_sentinels_of_a_column_are_counted_and_left_aside(source: Source) -> None:
    counted = {column.name: column for column in count(source, "ord", {}).columns}
    code = counted["dlvr_pst_cd"]
    assert code.statistics.sentinels == (Value("", 12400),), "the empty texts"
    assert code.statistics.lengths == Lengths(5, 5), "without the empty texts"
    assert code.statistics.nulls == 0, "the nulls apart"
    day = counted["dlvr_dt"].statistics
    assert day.sentinels == (Value("9999-12-31", 300),)
    assert day.range is not None
    assert day.range.largest != "9999-12-31", "the range without the sentinels"
    assert counted["ord_id"].statistics.sentinels == (), "a column of none"
    segment = {column.name: column for column in count(source, "cust", {}).columns}["seg_cd"]
    assert segment.statistics.sentinels == (Value("N/A", 60), Value("", 40)), "each, most first"


def test_the_sentinels_given_of_a_column_are_counted_in_place_of_those_of_the_tool(
    source: Source,
) -> None:
    given = {"dlvr_pst_cd": ("00000",), "dlvr_dt": ()}
    counted = {column.name: column for column in count(source, "ord", given).columns}
    code = counted["dlvr_pst_cd"]
    assert code.sentinels == ("00000",), "the column with the sentinels it was counted with"
    assert code.statistics.sentinels == (), "no empty text is one"
    assert code.statistics.lengths == Lengths(0, 5)
    assert counted["dlvr_dt"].statistics.sentinels == (), "none where they are none"
    assert counted["ord_id"].sentinels is None, "those of the tool"


class _Counted(Source):
    """A schema of one table `t` of one column `b` of the type `kind`, which counts one row of it.

    It answers each statement that counts by `row`, and keeps them.
    """

    def __init__(self, kind: str, row: tuple[object, ...]) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("c", "s", trino.dialect)
        self.statements: list[str] = []
        self._kind = kind
        self._row = row

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        if "information_schema" in statement:
            return [("b", self._kind)]
        self.statements.append(statement)
        return [self._row]

    def close(self) -> None:
        pass


def test_a_column_of_no_text_is_counted_without_the_sentinels_given_of_it() -> None:
    # The rows, and of `b` its nulls and its distinct values.
    (column,) = count(_Counted("varbinary", (1, 0, 1)), "t", {"b": ("",)}).columns
    assert column.sentinels is None, "counted with none"
    assert column.statistics.sentinels == ()


def test_a_column_is_counted_with_those_of_the_sentinels_given_its_type_can_hold() -> None:
    # The rows, and of `b` its nulls, its distinct values, the rows of `-1`, its range.
    source = _Counted("bigint", (1, 0, 1, 0, "7", "7"))
    (column,) = count(source, "t", {"b": ("N/A", "-1")}).columns
    (statement,) = source.statements
    assert "'-1'" in statement
    assert "'N/A'" not in statement, "a number cannot be one"
    assert column.sentinels == ("N/A", "-1"), "the sentinels given"
