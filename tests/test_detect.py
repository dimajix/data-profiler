"""Tests of detection: each detector on values of its type and on values that are not."""

from datetime import date, datetime

import pytest

from data_profiler.detect import SemanticType, Sensitivity, detect

_RECOGNISED = {
    SemanticType.EMAIL: ["anna.schmidt@example.de", "a+b@mail.example.co.uk", "X_1@host.org"],
    SemanticType.PHONE: ["+49 30 12345678", "030 1234567", "(030) 1234567", "0171/1234567"],
    SemanticType.POSTAL_CODE: ["10115", "01067", "99998"],
    SemanticType.IBAN: [
        "DE89370400440532013000",
        "DE89 3704 0044 0532 0130 00",
        "RU02 0445 2560 0407 0281 0412 3456 7890 1",
    ],
    SemanticType.CARD_NUMBER: ["4111111111111111", "4111 1111 1111 1111", "5500-0000-0000-0004"],
    SemanticType.DATE: [
        "2024-02-29",
        "29.02.2024",
        "2024-01-31 23:59",
        "2024-01-31T23:59:59",
        "2024-01-31 23:59:59.123456789",
        "2024-01-31 12:00:00+00:00",
        "2024-01-31 12:00:00.000 UTC",
        "2024-01-31T12:00:00Z",
    ],
}

_NOT_RECOGNISED = {
    SemanticType.EMAIL: ["anna.schmidt", "anna@localhost", "@example.de", "a b@example.de"],
    SemanticType.PHONE: ["2024-01-01", "05.03.2024", "0.453219", "12345", "030 12", "+49 30 abc"],
    SemanticType.POSTAL_CODE: ["00999", "1011", "101155", "A1011"],
    SemanticType.IBAN: ["DE89370400440532013001", "DE89", "de89370400440532013000"],
    SemanticType.CARD_NUMBER: ["4111111111111112", "1111111111111117", "411111111111"],
    SemanticType.DATE: [
        "2023-02-29",
        "31.04.2024",
        "31.13.2024",
        "2024-01-31 24:00",
        "20240131",
        "2024/01/31",
    ],
}


@pytest.mark.parametrize(
    ("kind", "value"),
    [(kind, value) for kind, values in _RECOGNISED.items() for value in values],
    ids=str,
)
def test_a_value_of_a_type_is_recognised(kind: SemanticType, value: str) -> None:
    assert kind.detector.recognises(value)


@pytest.mark.parametrize(
    ("kind", "value"),
    [(kind, value) for kind, values in _NOT_RECOGNISED.items() for value in values],
    ids=str,
)
def test_a_value_of_another_kind_is_not_recognised(kind: SemanticType, value: str) -> None:
    assert not kind.detector.recognises(value)


@pytest.mark.parametrize(
    ("kind", "sensitivity"),
    [
        (SemanticType.EMAIL, Sensitivity.PERSONAL),
        (SemanticType.PHONE, Sensitivity.PERSONAL),
        (SemanticType.POSTAL_CODE, Sensitivity.NONE),
        (SemanticType.IBAN, Sensitivity.PERSONAL),
        (SemanticType.CARD_NUMBER, Sensitivity.PAYMENT_CARD),
        (SemanticType.DATE, Sensitivity.NONE),
    ],
    ids=str,
)
def test_every_semantic_type_has_its_sensitivity(
    kind: SemanticType, sensitivity: Sensitivity
) -> None:
    assert kind.sensitivity == sensitivity


def test_the_share_of_the_values_of_each_type_is_detected_nulls_aside() -> None:
    values = ["10115", "01067", None, "anna@example.de", "nothing", None]
    assert detect(values) == {SemanticType.POSTAL_CODE: 0.5, SemanticType.EMAIL: 0.25}


def test_values_of_any_type_are_detected_as_text() -> None:
    assert detect([date(2024, 1, 31), datetime(2024, 1, 31, 12, 0)]) == {SemanticType.DATE: 1.0}
    assert detect([10115, 99998]) == {SemanticType.POSTAL_CODE: 1.0}


def test_values_are_detected_without_the_spaces_at_their_ends() -> None:
    assert detect([" 10115", "10115   "]) == {SemanticType.POSTAL_CODE: 1.0}


@pytest.mark.parametrize("values", [[], [None, None]], ids=["no values", "only nulls"])
def test_no_type_is_detected_without_values(values: list[object]) -> None:
    assert detect(values) == {}
