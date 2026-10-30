"""Tests of the enumerations of tables, against the simulation environment, which has to run."""

from data_profiler.enumerations import values
from data_profiler.profile import Profile
from data_profiler.source import Source
from data_profiler.statistics import count


def test_the_columns_of_few_values_that_repeat_are_enumerations(
    source: Source, example: Profile
) -> None:
    for made in example.tables:
        expected = [
            column.name
            for column in made.columns
            if column.statistics.distinct <= 500
            and column.statistics.distinct < made.rows - column.statistics.nulls
        ]
        enumerations = values(source, count(source, made.name))
        assert [enumeration.column for enumeration in enumerations] == expected, made.name


def test_the_values_of_an_enumeration_are_counted_on_the_whole_table(
    source: Source, example: Profile
) -> None:
    for made in example.tables:
        statistics = {column.name: column.statistics for column in made.columns}
        for enumeration in values(source, count(source, made.name)):
            where = f"{made.name}.{enumeration.column}"
            found = statistics[enumeration.column]
            assert len(enumeration.values) == found.distinct, where
            counts = [rows for _, rows in enumeration.values]
            assert sum(counts) == made.rows - found.nulls, f"{where}: every row but the nulls"
            assert counts == sorted(counts, reverse=True), f"{where}: the most frequent first"
            assert None not in [value for value, _ in enumeration.values], where
