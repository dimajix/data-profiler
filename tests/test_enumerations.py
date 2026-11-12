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
            and column.statistics.distinct
            < made.rows - column.statistics.nulls - column.statistics.sentinel_rows
        ]
        enumerations = values(source, count(source, made.name, {}))
        assert [enumeration.column for enumeration in enumerations] == expected, made.name


def test_the_values_of_an_enumeration_are_counted_on_the_whole_table(
    source: Source, example: Profile
) -> None:
    for made in example.tables:
        statistics = {column.name: column.statistics for column in made.columns}
        for enumeration in values(source, count(source, made.name, {})):
            where = f"{made.name}.{enumeration.column}"
            found = statistics[enumeration.column]
            assert len(enumeration.values) == found.distinct, f"{where}: its sentinels aside"
            counts = [rows for _, rows in enumeration.values]
            rest = made.rows - found.nulls - found.sentinel_rows
            assert sum(counts) == rest, f"{where}: every row but its nulls and sentinels"
            assert counts == sorted(counts, reverse=True), f"{where}: the most frequent first"
            assert None not in [value for value, _ in enumeration.values], where


def test_the_values_of_an_enumeration_are_the_texts_the_database_writes(source: Source) -> None:
    enumerations = {found.column: found for found in values(source, count(source, "cust", {}))}
    assert {value for value, _ in enumerations["actv_flg"].values} == {"true", "false"}
