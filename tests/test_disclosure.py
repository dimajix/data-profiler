"""Tests of disclosure: the values of a table the profile may hold, of a table made by hand."""

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.disclosure import disclose
from data_profiler.profile import Column, Match, Range, Statistics, Table, Value

_VALUES = (Value("10115", 7), Value("99998", 3))


def _disclosed(column: Column) -> Column:
    """`column`, as the profile may hold it."""
    (disclosed,) = disclose(Table(name="t", rows=10, columns=(column,))).columns
    return disclosed


def _code(*matches: Match, marked: Sensitivity | None = None) -> Column:
    """A column of an enumeration with a range, `matches` and `marked`."""
    return Column(
        name="code",
        type="varchar(5)",
        statistics=Statistics(0, 2, range=Range("10115", "99998")),
        matches=matches,
        values=_VALUES,
        marked=marked,
    )


def test_a_column_of_no_sensitivity_keeps_its_range_and_its_values() -> None:
    column = _disclosed(_code(Match(SemanticType.POSTAL_CODE, 1.0, 1.0)))
    assert column.statistics.range == Range("10115", "99998")
    assert column.values == _VALUES


def test_a_column_no_detector_recognises_is_of_no_sensitivity() -> None:
    assert _disclosed(_code()).values == _VALUES


def test_a_column_of_a_sensitivity_keeps_neither_its_range_nor_its_values() -> None:
    column = _disclosed(_code(Match(SemanticType.POSTAL_CODE, 0.6), Match(SemanticType.PHONE, 0.5)))
    assert column.statistics.range is None
    assert column.values == ()


def test_a_column_marked_sensitive_keeps_neither_its_range_nor_its_values() -> None:
    column = _disclosed(_code(marked=Sensitivity.PERSONAL))
    assert (column.statistics.range, column.values) == (None, ())


def test_a_mark_comes_before_the_matches() -> None:
    column = _code(Match(SemanticType.PHONE, 1.0, 1.0), marked=Sensitivity.NONE)
    assert column.sensitivity is Sensitivity.NONE
    assert _disclosed(column).values == _VALUES


def test_a_value_of_a_sensitive_type_is_withheld_from_a_column_of_no_sensitivity() -> None:
    column = Column(
        name="contact",
        type="varchar(40)",
        statistics=Statistics(0, 3, range=Range("Anna", "anna@example.de")),
        values=(Value("Anna", 5), Value("+49 30 1234567", 3), Value("DE89370400440532013000", 1)),
    )
    disclosed = _disclosed(column)
    assert disclosed.statistics.range == Range("Anna", None)
    assert disclosed.values == (Value("Anna", 5),)


def test_a_range_of_which_both_ends_are_withheld_is_none() -> None:
    column = Column(
        name="contact",
        type="varchar(40)",
        statistics=Statistics(0, 2, range=Range("+49 30 1234567", "anna@example.de")),
    )
    assert _disclosed(column).statistics.range is None


def test_a_long_value_is_cut_to_a_hundred_characters() -> None:
    long = "a" * 150
    column = Column(
        name="note",
        type="varchar(4000)",
        statistics=Statistics(0, 2, range=Range("b", long)),
        values=(Value(long, 2), Value("b", 1)),
    )
    cut = "a" * 99 + "…"
    disclosed = _disclosed(column)
    assert disclosed.statistics.range == Range("b", cut)
    assert disclosed.values == (Value(cut, 2), Value("b", 1))


def test_a_table_disclosed_again_is_disclosed_as_before() -> None:
    table = Table(name="t", rows=10, columns=(_code(), _code(marked=Sensitivity.PERSONAL)))
    assert disclose(disclose(table)) == disclose(table)
