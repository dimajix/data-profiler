"""Tests of the statistics of a table, against the simulation environment, which has to run."""

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
    """A schema of one table `t` of one column `b` of binaries, which counts one row of it."""

    def __init__(self) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("c", "s", trino.dialect)

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        if "information_schema" in statement:
            return [("b", "varbinary")]
        # The rows, and of `b` its nulls and its distinct values.
        return [(1, 0, 1)]

    def close(self) -> None:
        pass


def test_a_column_of_no_text_is_counted_without_the_sentinels_given_of_it() -> None:
    (column,) = count(_Counted(), "t", {"b": ("",)}).columns
    assert column.sentinels is None, "counted with none"
    assert column.statistics.sentinels == ()
