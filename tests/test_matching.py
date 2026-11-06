"""Tests of the matches of a table: recognised in a sample made by hand, verified on a table."""

import re
from dataclasses import replace

from data_profiler.detect import (
    BUILT_IN,
    CURRENCY_NAME,
    DATE,
    FREE_TEXT,
    POSTAL_CODE,
    Detector,
    SemanticType,
    Sensitivity,
)
from data_profiler.matching import recognise, verify
from data_profiler.profile import Column, Match, Statistics, Table, Value
from data_profiler.source import Source
from data_profiler.statistics import count
from data_profiler.workspace import Sample


def _matches(
    values: list[object], *types: SemanticType, sentinels: tuple[Value, ...] = ()
) -> tuple[Match, ...]:
    """The matches of a column of `values`, as its sample holds them, in a project of `types`."""
    statistics = Statistics(0, len(values), sentinels=sentinels)
    column = Column(name="value", type="varchar(40)", statistics=statistics)
    table = Table(name="table", rows=len(values), columns=(column,))
    (matched,) = recognise(table, Sample(columns={"value": values}), types).columns
    return matched.matches


def test_a_type_recognised_in_half_of_the_values_is_a_match() -> None:
    assert _matches(["10115", "anna"]) == (Match(POSTAL_CODE, 0.5),)


def test_a_type_recognised_in_less_than_half_of_the_values_is_no_match() -> None:
    assert _matches(["10115", "anna", "otto"]) == ()


def test_the_nulls_of_a_sample_are_not_counted() -> None:
    assert _matches(["10115", None, None, None]) == (Match(POSTAL_CODE, 1.0),)


def test_the_sentinels_of_a_sample_are_not_counted_where_the_table_has_any() -> None:
    values: list[object] = ["10115", "", "N/A", "-"]
    found = (Value("", 1), Value("-", 1), Value("N/A", 1))
    assert _matches(values, sentinels=found) == (Match(POSTAL_CODE, 1.0),)
    assert _matches(values) == (), "counted where the statistics counted none"


def test_every_type_recognised_in_half_of_the_values_is_a_match() -> None:
    matches = _matches(["10115", "2024-01-31"])
    assert sorted(match.type.name for match in matches) == ["date", "postal-code"]


def test_a_type_recognised_in_the_threshold_of_its_detector_is_a_match() -> None:
    pair = SemanticType(
        "pair", Sensitivity.NONE, Detector(re.compile("[0-9]+ [0-9]+"), threshold=0.25)
    )
    values: list[object] = ["ok", "ok", "ok", "1 2"]
    assert _matches(values, pair) == (Match(pair, 0.25),)
    assert _matches(["ok", *values], pair) == (), "a fifth is less than a quarter"


def test_a_type_of_the_project_is_recognised(account_number: SemanticType) -> None:
    assert _matches(["A0123456789", "A9876543210"], account_number) == (Match(account_number, 1.0),)


def test_a_share_is_written_with_three_digits() -> None:
    assert _matches(["10115", "10117", "anna"]) == (Match(POSTAL_CODE, 0.667),)


def _verified(source: Source, table: str, column: str, kinds: list[SemanticType]) -> list[Match]:
    """The matches of `kinds` of `column` of `table`, as the simulation verifies them."""
    counted = count(source, table, {})
    columns = tuple(
        replace(found, matches=tuple(Match(kind, 1.0) for kind in kinds))
        if found.name == column
        else found
        for found in counted.columns
    )
    (verified,) = [
        c for c in verify(source, replace(counted, columns=columns)).columns if c.name == column
    ]
    return list(verified.matches)


def test_a_match_is_verified_by_the_share_of_the_table_its_pattern_matches(
    source: Source,
) -> None:
    assert _verified(source, "cust", "upd_ts", [DATE]) == [Match(DATE, 1.0, 1.0)], (
        "the nulls of the table are not counted"
    )


def test_a_match_is_verified_without_the_sentinels_of_the_table(source: Source) -> None:
    assert _verified(source, "ord", "dlvr_pst_cd", [POSTAL_CODE]) == [
        Match(POSTAL_CODE, 1.0, 1.0)
    ], "the empty texts of the table are not counted"
    assert _verified(source, "ord", "dlvr_dt", [DATE]) == [Match(DATE, 1.0, 1.0)], (
        "nor its last days, which the pattern of a date matches"
    )


def test_the_pattern_of_every_type_is_read_by_the_database(source: Source) -> None:
    kinds = list(BUILT_IN)
    shares = {m.type: m.table for m in _verified(source, "cust", "crt_dt", kinds)}
    assert shares == {kind: 1.0 if kind is DATE else 0.0 for kind in kinds}


def test_the_pattern_of_names_of_currencies_takes_their_characters_as_written(
    source: Source,
) -> None:
    names = [
        "Mexican Unidad de Inversion (UDI)",
        "Pa\u2019anga",
        "Pa'anga",
        "Bolívar Soberano",
        "Mexican UDI",
    ]
    values = ", ".join(f"""('{name.replace("'", "''")}')""" for name in names)
    matching = source.dialect.matching("name", CURRENCY_NAME.detector.pattern.pattern)
    statement = f"SELECT {matching} FROM (VALUES {values}) AS names (name)"
    assert source.query(statement, "matching names") == [(4,)], "all but the last"


def test_a_share_of_a_column_of_numbers_is_written_with_three_digits(source: Source) -> None:
    (match,) = _verified(source, "ord_itm", "ord_itm_id", [POSTAL_CODE])
    assert match.table is not None
    assert 0 < match.table < 1, "some of the identifiers are numbers of five digits, not all"
    assert match.table == round(match.table, 3)


def test_a_match_of_a_column_of_no_text_is_not_verified(source: Source) -> None:
    statistics = Statistics(0, 1)
    column = Column("value", "varbinary", statistics, matches=(Match(FREE_TEXT, 1.0),))
    table = Table(name="no such table", rows=1, columns=(column,))
    assert verify(source, table) is table, "the database casts no binary to a text"


def test_a_table_without_matches_is_not_queried(source: Source) -> None:
    column = Column(name="value", type="varchar(40)", statistics=Statistics(0, 1))
    table = Table(name="no such table", rows=1, columns=(column,))
    assert verify(source, table) is table, "a query of a table that does not exist would fail"
