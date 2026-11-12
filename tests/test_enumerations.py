"""Tests of the enumerations of tables, against the simulation environment, which has to run."""

from dataclasses import replace

import pytest

from data_profiler.detect import DATE, TRUE_FALSE, UUID
from data_profiler.enumerations import values
from data_profiler.profile import Column, Match, Profile, Table
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
            and source.dialect.is_enumerable(column.type)
            and column.statistics.distinct
            < made.rows - column.statistics.nulls - column.statistics.sentinel_rows
        ]
        enumerations = values(source, count(source, made.name, {}), {})
        assert [enumeration.column for enumeration in enumerations] == expected, made.name


def test_the_values_of_an_enumeration_are_counted_on_the_whole_table(
    source: Source, example: Profile
) -> None:
    for made in example.tables:
        statistics = {column.name: column.statistics for column in made.columns}
        for enumeration in values(source, count(source, made.name, {}), {}):
            where = f"{made.name}.{enumeration.column}"
            found = statistics[enumeration.column]
            assert len(enumeration.values) == found.distinct, f"{where}: its sentinels aside"
            counts = [rows for _, rows in enumeration.values]
            rest = made.rows - found.nulls - found.sentinel_rows
            assert sum(counts) == rest, f"{where}: every row but its nulls and sentinels"
            assert counts == sorted(counts, reverse=True), f"{where}: the most frequent first"
            assert None not in [value for value, _ in enumeration.values], where


def test_the_values_of_an_enumeration_are_the_texts_the_database_writes(source: Source) -> None:
    enumerations = {found.column: found for found in values(source, count(source, "cust", {}), {})}
    assert {value for value, _ in enumerations["actv_flg"].values} == {"true", "false"}


def _with(table: Table, changed: Column) -> Table:
    columns = (changed if column.name == changed.name else column for column in table.columns)
    return replace(table, columns=tuple(columns))


def test_a_column_of_a_type_whose_values_no_closed_list_holds_is_no_enumeration(
    source: Source, example: Profile
) -> None:
    counted = count(source, "cust", {})
    assert "actv_flg" in [found.column for found in values(source, counted, {})]
    for kind in ("date", "uuid", "double"):
        changed = _with(counted, replace(counted.column("actv_flg"), type=kind))
        assert "actv_flg" not in [found.column for found in values(source, changed, {})], kind


def test_a_column_of_a_match_of_a_semantic_type_that_is_none_is_no_enumeration(
    source: Source, example: Profile
) -> None:
    counted = count(source, "cust", {})
    for kind, enumeration in ((UUID, False), (DATE, False), (TRUE_FALSE, True)):
        matches = (Match(TRUE_FALSE, 1.0), Match(kind, 0.5))
        matched = _with(counted, replace(counted.column("actv_flg"), matches=matches))
        found = [found.column for found in values(source, matched, {})]
        assert ("actv_flg" in found) == enumeration, kind.name


def test_a_column_of_lists_is_no_enumeration_of_its_texts(source: Source, example: Profile) -> None:
    counted = count(source, "prod", {})
    assert "sale_curr_cds" in [found.column for found in values(source, counted, {})]
    listed = _with(counted, replace(counted.column("sale_curr_cds"), list_separator=";"))
    assert "sale_curr_cds" not in [found.column for found in values(source, listed, {})]


def test_a_column_given_as_an_enumeration_is_one_whatever_its_type_and_its_values(
    source: Source, example: Profile
) -> None:
    counted = count(source, "cust", {})
    dated = _with(counted, replace(counted.column("actv_flg"), type="date"))
    assert "actv_flg" in [found.column for found in values(source, dated, {"actv_flg": True})]
    products = count(source, "prod", {})
    assert "prod_cd" not in [found.column for found in values(source, products, {})]
    found = {found.column: found for found in values(source, products, {"prod_cd": True})}
    assert len(found["prod_cd"].values) == 350, "of values each in one row alone"


def test_a_column_given_as_no_enumeration_is_none(source: Source, example: Profile) -> None:
    counted = count(source, "cust", {})
    found = [found.column for found in values(source, counted, {"actv_flg": False})]
    assert "actv_flg" not in found
    assert "cust_typ_cd" in found, "a column not given is found as ever"


def test_a_column_given_as_an_enumeration_of_more_values_than_one_has_is_none_warned_of(
    source: Source, example: Profile, caplog: pytest.LogCaptureFixture
) -> None:
    counted = count(source, "cust", {})
    found = [found.column for found in values(source, counted, {"cust_id": True})]
    assert "cust_id" not in found
    assert "give cust_id of " in caplog.text
    assert "5000 distinct values, more than an enumeration has, 500" in caplog.text


def test_a_column_of_lists_given_as_an_enumeration_is_none_of_its_texts(
    source: Source, example: Profile
) -> None:
    counted = count(source, "prod", {})
    listed = _with(counted, replace(counted.column("sale_curr_cds"), list_separator=";"))
    given = {"sale_curr_cds": True}
    assert "sale_curr_cds" not in [found.column for found in values(source, listed, given)]
