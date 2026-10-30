"""Tests of the statistics of a table, against the simulation environment, which has to run."""

import pytest

from data_profiler.profile import Range
from data_profiler.source import Source, SourceError
from data_profiler.statistics import count


def test_only_a_column_of_texts_has_its_lengths_counted(source: Source) -> None:
    counted = {column.name: column.statistics for column in count(source, "cust").columns}
    assert counted["cust_nm"].lengths is not None
    assert counted["crt_dt"].lengths is None
    assert counted["crdt_lmt_amt"].lengths is None


def test_the_range_of_a_column_whose_values_have_an_order_is_counted_as_text(
    source: Source,
) -> None:
    counted = {column.name: column.statistics for column in count(source, "cust").columns}
    assert counted["actv_flg"].range == Range("false", "true")
    for name in ("cust_id", "cust_nm", "crt_dt", "upd_ts", "crdt_lmt_amt"):
        assert counted[name].range is not None, name


def test_a_table_that_does_not_exist_is_not_counted(source: Source) -> None:
    with pytest.raises(SourceError, match="has no table nowhere"):
        count(source, "nowhere")
