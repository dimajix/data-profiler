"""Tests of detection: each detector on values of its type and on values that are not."""

import re
from datetime import date, datetime

import pytest

from data_profiler.detect import (
    CARD_NUMBER,
    DATE,
    EMAIL,
    IBAN,
    PHONE,
    POSTAL_CODE,
    UUID,
    Detector,
    SemanticType,
    SemanticTypeError,
    Sensitivity,
    detect,
    is_sensitive,
    project_type,
    semantic_type,
)

_RECOGNISED = {
    EMAIL: ["anna.schmidt@example.de", "a+b@mail.example.co.uk", "X_1@host.org"],
    PHONE: ["+49 30 12345678", "030 1234567", "(030) 1234567", "0171/1234567"],
    POSTAL_CODE: ["10115", "01067", "99998"],
    IBAN: [
        "DE89370400440532013000",
        "DE89 3704 0044 0532 0130 00",
        "RU02 0445 2560 0407 0281 0412 3456 7890 1",
    ],
    CARD_NUMBER: ["4111111111111111", "4111 1111 1111 1111", "5500-0000-0000-0004"],
    DATE: [
        "2024-02-29",
        "29.02.2024",
        "2024-01-31 23:59",
        "2024-01-31T23:59:59",
        "2024-01-31 23:59:59.123456789",
        "2024-01-31 12:00:00+00:00",
        "2024-01-31 12:00:00.000 UTC",
        "2024-01-31T12:00:00Z",
    ],
    UUID: [
        "123e4567-e89b-12d3-a456-426614174000",
        "F81D4FAE-7DEC-11D0-A765-00A0C91E6BF6",
        "00000000-0000-0000-0000-000000000000",
    ],
}

_NOT_RECOGNISED = {
    EMAIL: ["anna.schmidt", "anna@localhost", "@example.de", "a b@example.de"],
    PHONE: ["2024-01-01", "05.03.2024", "0.453219", "12345", "030 12", "+49 30 abc"],
    POSTAL_CODE: ["00999", "1011", "101155", "A1011"],
    IBAN: ["DE89370400440532013001", "DE89", "de89370400440532013000"],
    CARD_NUMBER: ["4111111111111112", "1111111111111117", "411111111111"],
    DATE: [
        "2023-02-29",
        "31.04.2024",
        "31.13.2024",
        "2024-01-31 24:00",
        "20240131",
        "2024/01/31",
    ],
    UUID: [
        "123e4567e89b12d3a456426614174000",
        "{123e4567-e89b-12d3-a456-426614174000}",
        "123e4567-e89b-12d3-a456-42661417400",
        "123e4567-e89b-12d3-a456-42661417400g",
        "123e4567-e89b-12d3a456-426614174000",
    ],
}


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        pytest.param(kind, value, id=f"{kind.name}-{value}")
        for kind, values in _RECOGNISED.items()
        for value in values
    ],
)
def test_a_value_of_a_type_is_recognised(kind: SemanticType, value: str) -> None:
    assert kind.detector.recognises(value)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        pytest.param(kind, value, id=f"{kind.name}-{value}")
        for kind, values in _NOT_RECOGNISED.items()
        for value in values
    ],
)
def test_a_value_of_another_kind_is_not_recognised(kind: SemanticType, value: str) -> None:
    assert not kind.detector.recognises(value)


@pytest.mark.parametrize(
    ("kind", "sensitivity"),
    [
        pytest.param(kind, sensitivity, id=kind.name)
        for kind, sensitivity in [
            (EMAIL, Sensitivity.PERSONAL),
            (PHONE, Sensitivity.PERSONAL),
            (POSTAL_CODE, Sensitivity.NONE),
            (IBAN, Sensitivity.PERSONAL),
            (CARD_NUMBER, Sensitivity.PAYMENT_CARD),
            (DATE, Sensitivity.NONE),
            (UUID, Sensitivity.NONE),
        ]
    ],
)
def test_every_semantic_type_has_its_sensitivity(
    kind: SemanticType, sensitivity: Sensitivity
) -> None:
    assert kind.sensitivity == sensitivity


def test_the_share_of_the_values_of_each_type_is_detected_nulls_aside() -> None:
    values = ["10115", "01067", None, "anna@example.de", "otto@example.de", None]
    assert detect(values, ()) == {POSTAL_CODE: 0.5, EMAIL: 0.5}


def test_a_type_recognised_in_less_than_the_threshold_of_its_detector_is_not_detected() -> None:
    assert detect(["10115", "anna", "otto"], ()) == {}, "a third is less than half"


def test_values_of_any_type_are_detected_as_text() -> None:
    assert detect([date(2024, 1, 31), datetime(2024, 1, 31, 12, 0)], ()) == {DATE: 1.0}
    assert detect([10115, 99998], ()) == {POSTAL_CODE: 1.0}


def test_values_are_detected_without_the_spaces_at_their_ends() -> None:
    assert detect([" 10115", "10115   "], ()) == {POSTAL_CODE: 1.0}


@pytest.mark.parametrize("values", [[], [None, None]], ids=["no values", "only nulls"])
def test_no_type_is_detected_without_values(values: list[object]) -> None:
    assert detect(values, ()) == {}


# Recognises digits, of a column of at most two distinct values.
_PAIR = Detector(re.compile("[0-9]"), column=lambda texts: len(set(texts)) <= 2)


def test_a_detector_shares_the_texts_it_recognises() -> None:
    assert Detector(re.compile("[0-9]+")).share(["1", "22", "a", "b"]) == 0.5


def test_a_detector_shares_nothing_of_no_texts() -> None:
    assert Detector(re.compile("[0-9]+")).share([]) == 0.0


def test_a_detector_shares_the_texts_of_a_column_that_meets_its_condition() -> None:
    assert _PAIR.share(["0", "1", "0", "1"]) == 1.0


def test_a_detector_shares_nothing_of_a_column_that_fails_its_condition() -> None:
    assert _PAIR.share(["0", "1", "2", "1"]) == 0.0, "three distinct values are no pair"


def test_a_type_whose_condition_of_the_column_fails_is_not_detected() -> None:
    pair = SemanticType("pair", Sensitivity.NONE, _PAIR)
    assert detect(["0", "1"], (pair,)) == {pair: 1.0}
    assert detect(["0", "1", "2"], (pair,)) == {}


@pytest.mark.parametrize(
    ("text", "sensitive"),
    [
        ("anna@example.de", True),
        (" +49 30 1234567 ", True),
        ("4111111111111111", True),
        ("10115", False),
        ("2024-01-31", False),
        ("Anna", False),
    ],
)
def test_a_text_of_a_type_of_a_sensitivity_is_sensitive(text: str, sensitive: bool) -> None:
    assert is_sensitive(text, ()) == sensitive


def test_a_type_of_a_project_is_detected_beside_those_of_the_tool(
    account_number: SemanticType,
) -> None:
    values = ["A0123456789", "10115"]
    assert detect(values, (account_number,)) == {POSTAL_CODE: 0.5, account_number: 0.5}


def test_a_text_of_a_type_of_a_project_of_a_sensitivity_is_sensitive(
    account_number: SemanticType,
) -> None:
    assert is_sensitive("A0123456789", (account_number,))
    assert not is_sensitive("A0123456789", ()), "a type of no project is not checked"


def test_a_semantic_type_is_found_by_its_name(account_number: SemanticType) -> None:
    assert semantic_type("uuid", ()) is UUID
    assert semantic_type("account-number", (account_number,)) is account_number
    assert semantic_type("account-number", ()) is None


def test_a_type_of_a_project_is_recognised_by_its_pattern(account_number: SemanticType) -> None:
    assert account_number.detector.recognises("A0123456789")
    assert not account_number.detector.recognises("A012345678")


@pytest.mark.parametrize(
    ("name", "pattern", "problem"),
    [
        ("email", "A[0-9]{10}", "email is a semantic type of the tool"),
        ("Account", "A[0-9]{10}", "'Account' is named other than in lower case letters"),
        ("account", "A[0-9", "the pattern of account is no regular expression"),
    ],
    ids=["a name of the tool", "a name in capitals", "no regular expression"],
)
def test_a_type_of_a_project_that_cannot_be_is_refused_naming_it(
    name: str, pattern: str, problem: str
) -> None:
    with pytest.raises(SemanticTypeError, match=re.escape(problem)):
        project_type(name, Sensitivity.PERSONAL, pattern)
