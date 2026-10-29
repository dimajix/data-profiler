"""Tests of the samples of tables, against the simulation environment, which has to run."""

from data_profiler.sampling import take
from data_profiler.source import Source
from data_profiler.statistics import count


def test_a_large_table_is_sampled_to_about_ten_thousand_rows(source: Source) -> None:
    table = count(source, "ord_itm")
    sample = take(source, table)
    assert list(sample.columns) == [column.name for column in table.columns]
    sizes = {len(values) for values in sample.columns.values()}
    assert len(sizes) == 1, "every column has a value for every row"
    assert 9_000 <= sizes.pop() <= 10_000


def test_a_small_table_is_taken_whole(source: Source) -> None:
    table = count(source, "prod")
    sample = take(source, table)
    keys = sample.columns["prod_id"]
    assert len(keys) == len(set(keys)) == table.rows, "every row once"
