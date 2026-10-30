"""Tests of the matches of a table, recognised in a sample made by hand."""

from data_profiler.detect import SemanticType
from data_profiler.matching import recognise
from data_profiler.profile import Column, Match, Statistics, Table
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
