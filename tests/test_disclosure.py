"""Tests of disclosure: the values of a table the profile may hold, of a table made by hand."""

from data_profiler.detect import SemanticType
from data_profiler.disclosure import disclose
from data_profiler.profile import Column, Match, Range, Statistics, Table, Value
from data_profiler.workspace import Enumeration


def _disclosed(*matches: Match) -> Column:
    """A column of an enumeration with a range and `matches`, as the profile may hold it."""
    column = Column(
        name="code",
        type="varchar(5)",
        statistics=Statistics(0, 2, range=Range("10115", "99998")),
        matches=matches,
    )
    enumeration = Enumeration(column="code", values=(("10115", 7), ("99998", 3)))
    (disclosed,) = disclose(Table(name="t", rows=10, columns=(column,)), [enumeration]).columns
    return disclosed


def test_a_column_of_no_sensitivity_has_its_range_and_its_values() -> None:
    column = _disclosed(Match(SemanticType.POSTAL_CODE, 1.0, 1.0))
    assert column.statistics.range == Range("10115", "99998")
    assert column.values == (Value("10115", 7), Value("99998", 3))


def test_a_column_no_detector_recognises_is_of_no_sensitivity() -> None:
    assert _disclosed().values == (Value("10115", 7), Value("99998", 3))


def test_a_column_of_a_sensitivity_has_neither_its_range_nor_its_values() -> None:
    column = _disclosed(Match(SemanticType.POSTAL_CODE, 0.6), Match(SemanticType.PHONE, 0.5))
    assert column.statistics.range is None
    assert column.values == ()


def test_the_values_of_an_enumeration_are_written_as_text() -> None:
    column = Column(name="pos", type="smallint", statistics=Statistics(0, 2))
    enumeration = Enumeration(column="pos", values=((1, 9), (2, 4)))
    (disclosed,) = disclose(Table(name="t", rows=13, columns=(column,)), [enumeration]).columns
    assert disclosed.values == (Value("1", 9), Value("2", 4))


def test_a_column_that_is_no_enumeration_has_no_values() -> None:
    column = Column(name="id", type="bigint", statistics=Statistics(0, 13))
    (disclosed,) = disclose(Table(name="t", rows=13, columns=(column,)), []).columns
    assert disclosed.values == ()


def test_a_value_of_a_sensitive_type_is_withheld_from_a_column_of_no_sensitivity() -> None:
    column = Column(
        name="contact",
        type="varchar(40)",
        statistics=Statistics(0, 3, range=Range("Anna", "anna@example.de")),
    )
    enumeration = Enumeration(
        column="contact", values=(("Anna", 5), ("+49 30 1234567", 3), ("DE89370400440532013000", 1))
    )
    (disclosed,) = disclose(Table(name="t", rows=9, columns=(column,)), [enumeration]).columns
    assert disclosed.statistics.range == Range("Anna", None)
    assert disclosed.values == (Value("Anna", 5),)


def test_a_range_of_which_both_ends_are_withheld_is_none() -> None:
    column = Column(
        name="contact",
        type="varchar(40)",
        statistics=Statistics(0, 2, range=Range("+49 30 1234567", "anna@example.de")),
    )
    (disclosed,) = disclose(Table(name="t", rows=2, columns=(column,)), []).columns
    assert disclosed.statistics.range is None


def test_a_long_value_is_cut_to_a_hundred_characters() -> None:
    long = "a" * 150
    column = Column(
        name="note", type="varchar(4000)", statistics=Statistics(0, 2, range=Range("b", long))
    )
    enumeration = Enumeration(column="note", values=((long, 2), ("b", 1)))
    (disclosed,) = disclose(Table(name="t", rows=3, columns=(column,)), [enumeration]).columns
    cut = "a" * 99 + "…"
    assert disclosed.statistics.range == Range("b", cut)
    assert disclosed.values == (Value(cut, 2), Value("b", 1))
