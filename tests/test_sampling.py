"""Tests of the samples of tables, against the simulation environment, which has to run."""

import re

from data_profiler.sampling import take
from data_profiler.source import Source
from data_profiler.statistics import count


def test_a_large_table_is_sampled_to_about_ten_thousand_rows(source: Source) -> None:
    table = count(source, "ord_itm", {})
    sample = take(source, table)
    assert list(sample.columns) == [column.name for column in table.columns]
    sizes = {len(values) for values in sample.columns.values()}
    assert len(sizes) == 1, "every column has a value for every row"
    assert 9_000 <= sizes.pop() <= 10_000


def test_a_small_table_is_taken_whole(source: Source) -> None:
    table = count(source, "prod", {})
    sample = take(source, table)
    keys = sample.columns["prod_id"]
    assert len(keys) == len(set(keys)) == table.rows, "every row once"


def test_a_sample_holds_the_values_as_the_texts_the_database_writes_of_all_their_digits(
    source: Source,
) -> None:
    sample = take(source, count(source, "cust", {}))
    moments = [value for value in sample.columns["upd_ts"] if value is not None]
    assert moments, "a sample of moments"
    for value in moments:
        assert isinstance(value, str)
        assert re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}", value
        )
    assert set(sample.columns["actv_flg"]) <= {"true", "false"}
