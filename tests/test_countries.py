"""Tests of countries: the codes, numbers and names of those of ISO 3166, current and withdrawn."""

import re

import pytest

from data_profiler.countries import ALPHA_2, ALPHA_3, NAMES, NUMBERS


@pytest.mark.parametrize(
    ("alpha_2", "alpha_3", "number", "name"),
    [
        ("DE", "DEU", "276", "Germany"),
        ("AT", "AUT", "040", "Austria"),
        ("KR", "KOR", "410", "Korea, Republic of"),
    ],
    ids=["DE", "AT", "KR"],
)
def test_a_current_country_is_known_by_its_codes_number_and_name(
    alpha_2: str, alpha_3: str, number: str, name: str
) -> None:
    assert alpha_2 in ALPHA_2
    assert alpha_3 in ALPHA_3
    assert number in NUMBERS
    assert name in NAMES


@pytest.mark.parametrize(
    ("alpha_2", "alpha_3", "number", "name"),
    [
        ("DD", "DDR", "278", "German Democratic Republic"),
        ("SU", "SUN", "810", "USSR, Union of Soviet Socialist Republics"),
        ("AN", "ANT", "530", "Netherlands Antilles"),
    ],
    ids=["DDR", "SUN", "ANT"],
)
def test_a_withdrawn_country_is_known_as_well(
    alpha_2: str, alpha_3: str, number: str, name: str
) -> None:
    assert alpha_2 in ALPHA_2
    assert alpha_3 in ALPHA_3
    assert number in NUMBERS
    assert name in NAMES


def test_a_country_is_known_by_its_official_and_its_common_name() -> None:
    assert {"Federal Republic of Germany", "South Korea", "Vietnam"} <= set(NAMES)


def test_a_country_is_known_by_a_name_more_common_than_those_of_iso() -> None:
    assert {"USA", "Russia", "Soviet Union", "Cote d'Ivoire"} <= set(NAMES)


def test_the_names_are_english_alone() -> None:
    assert not {"Deutschland", "Österreich", "Schweiz"} & set(NAMES)


def test_the_codes_are_of_two_and_three_capitals_and_the_numbers_of_three_digits() -> None:
    assert all(re.fullmatch("[A-Z]{2}", code) for code in ALPHA_2)
    assert all(re.fullmatch("[A-Z]{3}", code) for code in ALPHA_3)
    assert all(re.fullmatch("[0-9]{3}", number) for number in NUMBERS)


def test_each_code_number_and_name_is_given_once_in_order() -> None:
    for values in (ALPHA_2, ALPHA_3, NUMBERS, NAMES):
        assert list(values) == sorted(set(values))
