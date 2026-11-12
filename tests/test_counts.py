"""Tests of the counts of the database as the tool takes them: as numbers."""

import pytest

from data_profiler.counts import counted


def test_a_count_is_taken_as_the_number_it_is() -> None:
    assert counted(42, "cust") == 42


def test_a_count_that_is_no_number_is_refused_naming_where() -> None:
    with pytest.raises(TypeError, match=r"counted something of cust\.cust_id that is no number"):
        counted("42", "cust.cust_id")
