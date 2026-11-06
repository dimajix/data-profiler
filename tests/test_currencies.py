"""Tests of currencies: the codes, numbers and names of those of ISO 4217, current and withdrawn."""

import re

import pytest

from data_profiler.currencies import CODES, NAMES, NUMBERS


@pytest.mark.parametrize(
    ("code", "number", "name"),
    [("EUR", "978", "Euro"), ("CHF", "756", "Swiss Franc"), ("ALL", "008", "Lek")],
    ids=["EUR", "CHF", "ALL"],
)
def test_a_current_currency_is_known_by_its_code_number_and_name(
    code: str, number: str, name: str
) -> None:
    assert code in CODES
    assert number in NUMBERS
    assert name in NAMES


@pytest.mark.parametrize(
    ("code", "number", "name"),
    [("DEM", "276", "Deutsche Mark"), ("HRK", "191", "Kuna"), ("VEF", "937", "Bolivar Fuerte")],
    ids=["DEM", "HRK", "VEF"],
)
def test_a_currency_withdrawn_since_the_euro_is_known_as_well(
    code: str, number: str, name: str
) -> None:
    assert code in CODES
    assert number in NUMBERS
    assert name in NAMES


def test_a_currency_withdrawn_before_the_euro_is_not_known() -> None:
    assert "SUR" not in CODES, "the rouble of the Soviet Union, withdrawn in 1991"


def test_the_codes_of_no_currency_are_left_out() -> None:
    assert "XTS" not in CODES, "of testing"
    assert "XXX" not in CODES, "of no currency"


def test_a_currency_is_known_by_a_name_more_common_than_its_name_of_iso() -> None:
    assert {"British Pound", "Albanian Lek", "German Mark"} <= set(NAMES)


def test_the_names_that_are_words_of_other_columns_are_left_out_but_not_their_codes() -> None:
    words = {"Gold", "Silver", "Platinum", "Palladium", "Won", "Sol", "Rand", "Yen", "Sucre"}
    assert not (words | {"Pound", "Sterling"}) & set(NAMES), "tiers, stages, units"
    assert {"XAU", "XAG", "XPT", "XPD", "KRW", "PEN", "ZAR", "JPY"} <= set(CODES)
    assert {"Japanese Yen", "South Korean Won", "Pound Sterling"} <= set(NAMES), "nor their names"


def test_the_codes_are_of_three_capitals_and_the_numbers_of_three_digits() -> None:
    assert all(re.fullmatch("[A-Z]{3}", code) for code in CODES)
    assert all(re.fullmatch("[0-9]{3}", number) for number in NUMBERS)


def test_each_code_number_and_name_is_given_once_in_order() -> None:
    for values in (CODES, NUMBERS, NAMES):
        assert list(values) == sorted(set(values))
