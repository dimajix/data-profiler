"""Tests of disclosure: the values of a table the profile may hold, of a table made by hand."""

from dataclasses import replace

from data_profiler.detect import PHONE, POSTAL_CODE, SemanticType, Sensitivity
from data_profiler.disclosure import disclose, disclose_texts
from data_profiler.profile import (
    Column,
    Discriminator,
    Entity,
    Match,
    Range,
    Statistics,
    Table,
    Value,
)

_VALUES = (Value("10115", 7), Value("99998", 3))


def _disclosed(column: Column, *types: SemanticType) -> Column:
    """`column`, as the profile of a project of `types` may hold it."""
    (disclosed,) = disclose(Table(name="t", rows=10, columns=(column,)), types).columns
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
    column = _disclosed(_code(Match(POSTAL_CODE, 1.0, 1.0)))
    assert column.statistics.range == Range("10115", "99998")
    assert column.values == _VALUES


def test_a_column_no_detector_recognises_is_of_no_sensitivity() -> None:
    assert _disclosed(_code()).values == _VALUES


def test_a_column_of_a_sensitivity_keeps_neither_its_range_nor_its_values() -> None:
    column = _disclosed(_code(Match(POSTAL_CODE, 0.6), Match(PHONE, 0.5)))
    assert column.statistics.range is None
    assert column.values == ()


def test_a_column_marked_sensitive_keeps_neither_its_range_nor_its_values() -> None:
    column = _disclosed(_code(marked=Sensitivity.PERSONAL))
    assert column.sensitive
    assert (column.statistics.range, column.values) == (None, ())


def test_a_column_marked_sensitive_keeps_its_sentinels() -> None:
    sentinels = (Value("", 3), Value("N/A", 1))
    column = _code(marked=Sensitivity.PERSONAL)
    column = replace(column, statistics=replace(column.statistics, sentinels=sentinels))
    disclosed = _disclosed(column)
    assert disclosed.statistics.sentinels == sentinels, "no values of the column"
    assert (disclosed.statistics.range, disclosed.values) == (None, ())


def test_a_mark_comes_before_the_matches() -> None:
    column = _code(Match(PHONE, 1.0, 1.0), marked=Sensitivity.NONE)
    assert column.sensitivity is Sensitivity.NONE
    assert not column.sensitive
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


def _discriminated(column: Column) -> Table:
    """A table of `column`, whose values tell its entities apart, and of no other column."""
    entities = tuple(
        Entity((value.value,), value.rows, {column.name: value.rows}) for value in column.values
    )
    return Table(
        name="t", rows=10, columns=(column,), discriminator=Discriminator(column.name, entities)
    )


def test_a_discriminator_of_no_sensitivity_is_kept() -> None:
    table = _discriminated(_code())
    assert disclose(table, ()).discriminator == table.discriminator


def test_a_discriminator_marked_sensitive_is_dropped_with_its_values() -> None:
    table = _discriminated(_code(marked=Sensitivity.PERSONAL))
    assert disclose(table, ()).discriminator is None


def test_a_discriminator_of_a_value_withheld_is_dropped() -> None:
    values = (Value("Anna", 5), Value("+49 30 1234567", 5))
    table = _discriminated(Column("kind", "varchar(20)", Statistics(0, 2), values=values))
    assert disclose(table, ()).discriminator is None, "its entities are told apart by it"


def test_a_table_disclosed_again_is_disclosed_as_before() -> None:
    table = Table(name="t", rows=10, columns=(_code(), _code(marked=Sensitivity.PERSONAL)))
    assert disclose(disclose(table, ()), ()) == disclose(table, ())


def test_a_value_of_a_sensitive_type_of_the_project_is_withheld(
    account_number: SemanticType,
) -> None:
    column = Column(
        name="ref",
        type="varchar(11)",
        statistics=Statistics(0, 2, range=Range("A0123456789", "x")),
        values=(Value("A0123456789", 1), Value("x", 1)),
    )
    disclosed = _disclosed(column, account_number)
    assert disclosed.statistics.range == Range(None, "x")
    assert disclosed.values == (Value("x", 1),)


def test_the_texts_of_a_column_are_disclosed_as_its_values_are() -> None:
    texts = ["Anna", "+49 30 1234567", "x" * 120]
    assert list(disclose_texts(_code(), texts, ())) == ["Anna", "x" * 99 + "\u2026"], (
        "but of a sensitive type, and cut where long"
    )
    assert list(disclose_texts(_code(marked=Sensitivity.PERSONAL), texts, ())) == [], (
        "of none marked"
    )
    assert list(disclose_texts(_code(Match(PHONE, 0.9, 0.9)), texts, ())) == [], "of none matched"
