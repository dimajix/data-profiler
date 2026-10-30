"""Tests of the matches of a table: recognised in a sample made by hand, verified on a table."""

from dataclasses import replace

from data_profiler.detect import SemanticType
from data_profiler.matching import recognise, verify
from data_profiler.profile import Column, Match, Statistics, Table
from data_profiler.source import Source
from data_profiler.statistics import count
from data_profiler.workspace import Sample


def _matches(values: list[object]) -> tuple[Match, ...]:
    """The matches of a column of `values`, as its sample holds them."""
    column = Column(name="value", type="varchar(40)", statistics=Statistics(0, len(values)))
    table = Table(name="table", rows=len(values), columns=(column,))
    (matched,) = recognise(table, Sample(columns={"value": values})).columns
    return matched.matches


def test_a_type_recognised_in_half_of_the_values_is_a_match() -> None:
    assert _matches(["10115", "anna"]) == (Match(SemanticType.POSTAL_CODE, 0.5),)


def test_a_type_recognised_in_less_than_half_of_the_values_is_no_match() -> None:
    assert _matches(["10115", "anna", "otto"]) == ()


def test_the_nulls_of_a_sample_are_not_counted() -> None:
    assert _matches(["10115", None, None, None]) == (Match(SemanticType.POSTAL_CODE, 1.0),)


def test_every_type_recognised_in_half_of_the_values_is_a_match() -> None:
    matches = _matches(["10115", "2024-01-31"])
    assert sorted(match.type.value for match in matches) == ["date", "postal-code"]


def test_a_share_is_written_with_three_digits() -> None:
    assert _matches(["10115", "10117", "anna"]) == (Match(SemanticType.POSTAL_CODE, 0.667),)


def _verified(source: Source, table: str, column: str, kinds: list[SemanticType]) -> list[Match]:
    """The matches of `kinds` of `column` of `table`, as the simulation verifies them."""
    counted = count(source, table)
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
    assert _verified(source, "cust", "upd_ts", [SemanticType.DATE]) == [
        Match(SemanticType.DATE, 1.0, 1.0)
    ], "the nulls of the table are not counted"


def test_the_pattern_of_every_type_is_read_by_the_database(source: Source) -> None:
    kinds = list(SemanticType)
    shares = {m.type: m.table for m in _verified(source, "cust", "crt_dt", kinds)}
    assert shares == {kind: 1.0 if kind is SemanticType.DATE else 0.0 for kind in kinds}


def test_a_share_of_a_column_of_numbers_is_written_with_three_digits(source: Source) -> None:
    (match,) = _verified(source, "ord_itm", "pos_no", [SemanticType.POSTAL_CODE])
    assert match.table is not None
    assert 0 < match.table < 1, "some of the positions are numbers of five digits, not all"
    assert match.table == round(match.table, 3)


def test_a_table_without_matches_is_not_queried(source: Source) -> None:
    column = Column(name="value", type="varchar(40)", statistics=Statistics(0, 1))
    table = Table(name="no such table", rows=1, columns=(column,))
    assert verify(source, table) is table, "a query of a table that does not exist would fail"
