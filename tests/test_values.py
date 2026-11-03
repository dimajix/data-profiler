"""Tests of the values of the database as the tool takes them: counts as numbers, values as text."""

from decimal import Decimal

import pytest

from data_profiler.values import as_text, counted


def test_a_count_is_taken_as_the_number_it_is() -> None:
    assert counted(42, "cust") == 42


def test_a_count_that_is_no_number_is_refused_naming_where() -> None:
    with pytest.raises(TypeError, match=r"counted something of cust\.cust_id that is no number"):
        counted("42", "cust.cust_id")


@pytest.mark.parametrize(
    ("value", "text"),
    [(True, "true"), (False, "false"), (12, "12"), ("10115", "10115"), (Decimal("1.50"), "1.50")],
    ids=str,
)
def test_a_value_of_the_database_is_written_as_the_database_writes_it(
    value: object, text: str
) -> None:
    assert as_text(value) == text
