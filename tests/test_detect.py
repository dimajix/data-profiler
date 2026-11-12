"""Tests of detection: each detector on values of its type and on values that are not."""

import re
from collections.abc import Sequence
from datetime import date, datetime

import pytest

from data_profiler.detect import (
    CARD_NUMBER,
    COUNTRY_ALPHA_2,
    COUNTRY_ALPHA_3,
    COUNTRY_NAME,
    COUNTRY_NUMBER,
    CURRENCY_CODE,
    CURRENCY_NAME,
    CURRENCY_NUMBER,
    DATE,
    EMAIL,
    FREE_TEXT,
    IBAN,
    PHONE,
    POSTAL_CODE,
    SENTINELS,
    TRUE_FALSE,
    UUID,
    YES_NO,
    ZERO_ONE,
    Detector,
    SemanticType,
    SemanticTypeError,
    Sensitivity,
    all_types,
    cases,
    detect,
    is_list,
    is_list_separator,
    is_sensitive,
    project_type,
    semantic_type,
    sentinels,
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
    FREE_TEXT: [
        "Bitte Rückruf am Montag",
        "Kunde wünscht Lieferung an die Firma",
        "Customer asked for a refund.",
        "Rechnung\nkorrigiert und versandt",
    ],
    TRUE_FALSE: ["true", "False", "TRUE", "false"],
    YES_NO: ["yes", "No", "YES", "no"],
    ZERO_ONE: ["0", "1"],
    CURRENCY_CODE: ["EUR", "USD", "DEM", "XAU"],
    CURRENCY_NUMBER: ["978", "840", "008", "276"],
    CURRENCY_NAME: [
        "Euro",
        "euro",
        "US DOLLAR",
        "Pound Sterling",
        "British Pound",
        "Deutsche Mark",
        "Mexican Unidad de Inversion (UDI)",
        "Bolívar Soberano",
    ],
    COUNTRY_ALPHA_2: ["DE", "AT", "US", "DD", "SU"],
    COUNTRY_ALPHA_3: ["DEU", "AUT", "USA", "DDR", "YUG"],
    COUNTRY_NUMBER: ["276", "040", "840", "278"],
    COUNTRY_NAME: [
        "Germany",
        "germany",
        "GERMANY",
        "Federal Republic of Germany",
        "Korea, Republic of",
        "South Korea",
        "USA",
        "German Democratic Republic",
        "Soviet Union",
        "Côte d'Ivoire",
        "Cote d'Ivoire",
        "Cocos (Keeling) Islands",
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
    FREE_TEXT: ["ok", "Hans Müller", "Deutsche Bank AG", "Hauptstr. 5", "2024-01-31 12:00 UTC"],
    TRUE_FALSE: ["t", "f", "tRUE", "truth", "yes"],
    YES_NO: ["y", "n", "ja", "nein", "yES", "nope"],
    ZERO_ONE: ["2", "01", "10", "0.0", "-1"],
    CURRENCY_CODE: ["eur", "Eur", "EURO", "XXX", "XTS", "SUR"],
    CURRENCY_NUMBER: ["8", "08", "9780", "000", "97 8"],
    CURRENCY_NAME: ["Eur0", "Gold", "won", "Pound", "Mexican Unidad de Inversion UDI", "Mark"],
    COUNTRY_ALPHA_2: ["de", "De", "D", "DEU", "EN", "XX"],
    COUNTRY_ALPHA_3: ["deu", "Deu", "DE", "ABC", "XXX"],
    COUNTRY_NUMBER: ["40", "0276", "27 6", "000", "999"],
    COUNTRY_NAME: ["Deutschland", "Österreich", "England", "Germanyy", "Cocos Keeling Islands"],
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
            (FREE_TEXT, Sensitivity.NONE),
            (TRUE_FALSE, Sensitivity.NONE),
            (YES_NO, Sensitivity.NONE),
            (ZERO_ONE, Sensitivity.NONE),
            (CURRENCY_CODE, Sensitivity.NONE),
            (CURRENCY_NUMBER, Sensitivity.NONE),
            (CURRENCY_NAME, Sensitivity.NONE),
            (COUNTRY_ALPHA_2, Sensitivity.NONE),
            (COUNTRY_ALPHA_3, Sensitivity.NONE),
            (COUNTRY_NUMBER, Sensitivity.NONE),
            (COUNTRY_NAME, Sensitivity.NONE),
        ]
    ],
)
def test_every_semantic_type_has_its_sensitivity(
    kind: SemanticType, sensitivity: Sensitivity
) -> None:
    assert kind.sensitivity == sensitivity


def test_the_share_of_the_values_of_each_type_is_detected() -> None:
    values = ["10115", "01067", "anna@example.de", "otto@example.de"]
    assert detect(values, ()) == {POSTAL_CODE: 0.5, EMAIL: 0.5}


def test_a_type_recognised_in_less_than_the_threshold_of_its_detector_is_not_detected() -> None:
    assert detect(["10115", "anna", "otto"], ()) == {}, "a third is less than half"


def test_values_of_any_type_are_detected_as_text() -> None:
    assert detect([date(2024, 1, 31), datetime(2024, 1, 31, 12, 0)], ()) == {DATE: 1.0}
    assert detect([10115, 99998], ()) == {POSTAL_CODE: 1.0}


def test_values_are_detected_without_the_spaces_at_their_ends() -> None:
    assert detect([" 10115", "10115   "], ()) == {POSTAL_CODE: 1.0}


def test_the_sentinels_of_a_column_are_those_given_else_those_of_the_tool() -> None:
    assert sentinels(["", "00000"]) == {"", "00000"}
    assert sentinels(None) is SENTINELS, "those of the tool where none are given"
    assert sentinels([]) == frozenset(), "none where they are none"


def test_no_type_is_detected_without_values() -> None:
    assert detect([], ()) == {}


# Recognises digits, of a column of at most two distinct values.
_PAIR = Detector(re.compile("[0-9]"), column=lambda texts, _: len(set(texts)) <= 2)


def test_a_detector_shares_the_texts_it_recognises() -> None:
    assert Detector(re.compile("[0-9]+")).share(["1", "22", "a", "b"]) == 0.5


def test_a_detector_shares_nothing_of_no_texts() -> None:
    assert Detector(re.compile("[0-9]+")).share([]) == 0.0


def test_a_detector_shares_the_texts_of_a_column_that_meets_its_condition() -> None:
    assert _PAIR.share(["0", "1", "0", "1"]) == 1.0


def test_a_detector_shares_nothing_of_a_column_that_fails_its_condition() -> None:
    assert _PAIR.share(["0", "1", "2", "1"]) == 0.0, "three distinct values are no pair"


def test_a_condition_of_the_column_is_given_the_texts_its_detector_recognises() -> None:
    given: list[tuple[list[str], list[str]]] = []

    def condition(texts: Sequence[str], recognised: Sequence[str]) -> bool:
        given.append((list(texts), list(recognised)))
        return True

    detector = Detector(re.compile("[0-9]"), check=lambda value: value != "0", column=condition)
    assert detector.share(["0", "1", "a"]) == 1 / 3
    assert given == [(["0", "1", "a"], ["1"])], "the check refuses the 0, the pattern the a"


def test_a_type_whose_condition_of_the_column_fails_is_not_detected() -> None:
    pair = SemanticType("pair", Sensitivity.NONE, _PAIR)
    assert detect(["4", "7"], (pair,)) == {pair: 1.0}
    assert detect(["4", "7", "9"], (pair,)) == {}


# A column of comments, many of them short, and columns of several words each that are no free text.
_COMMENTS = [
    *["ok"] * 7,
    "Kunde bittet um Rückruf am Montag",
    "Lieferung kam beschädigt an, Ersatz wurde verschickt.",
    "Zahlung ist noch offen",
]
_NOT_FREE_TEXT = {
    "names": ["Hans Müller", "Anna Schmidt", "Hans von Müller", "Eva Maria Weber", "Otto Klein"],
    "addresses": ["Hauptstr. 5", "Am Markt 3", "Lindenallee 12a", "Berliner Str. 101", "Ring 7"],
    "products": ["Deutsche Bank AG", "Kaffee Crema 1 kg", "Apple iPhone 15 Pro", "Tee Grün 100 g"],
    "codes": ["AB 123 x45", "XZ 99 k12", "QQ 17 b33", "ZZ 42 a01"],
    "categories": ["neu angelegt", "neu angelegt", "in Arbeit", "in Arbeit", "neu angelegt"],
}


def test_a_column_of_free_text_is_detected_though_most_values_are_short_and_repeated() -> None:
    assert detect(_COMMENTS, ()) == {FREE_TEXT: 0.3}


@pytest.mark.parametrize(("kind", "values"), list(_NOT_FREE_TEXT.items()), ids=list(_NOT_FREE_TEXT))
def test_a_column_of_several_words_that_is_no_free_text_is_not_detected(
    kind: str, values: list[str]
) -> None:
    assert FREE_TEXT not in detect(values, ()), f"{kind} are no free text"


def test_a_column_of_booleans_is_one_of_true_and_false() -> None:
    assert detect(["true", "false", "true"], ()) == {TRUE_FALSE: 1.0}


def test_a_column_of_zeros_and_ones_is_one_of_a_pair() -> None:
    assert detect([0, 1, 1], ()) == {ZERO_ONE: 1.0}


def test_a_column_of_counts_mostly_zeros_and_ones_is_no_pair() -> None:
    assert detect([0, 1, 1, 0, 2], ()) == {}, "every value is of a pair, not most"


def test_a_column_of_codes_of_capitals_most_of_them_codes_of_currencies_is_none() -> None:
    codes = ["ALL", "TOP", "ALL", "TOP", "MID", "ALL", "TOP", "LOW"]
    assert detect(codes, ()) == {}, "three quarters of the values, not nearly every"


def test_a_column_of_flags_of_yes_and_no_is_no_column_of_codes_of_countries() -> None:
    flags = ["YES", "NO", "NO", "YES", "NO", "NO", "NO", "NO"]
    assert detect(flags, ()) == {YES_NO: 1.0}, "`NO` is Norway, but not nearly every"


@pytest.mark.parametrize(
    ("kind", "of_it", "other"),
    [
        (CURRENCY_CODE, "EUR", "ABC"),
        (CURRENCY_NUMBER, "978", "123"),
        (COUNTRY_ALPHA_2, "DE", "EN"),
        (COUNTRY_ALPHA_3, "DEU", "ABC"),
        (COUNTRY_NUMBER, "010", "123"),
    ],
    ids=[
        "currency-code",
        "currency-number",
        "country-alpha-2",
        "country-alpha-3",
        "country-number",
    ],
)
def test_a_column_of_codes_or_numbers_is_one_of_nearly_every_value(
    kind: SemanticType, of_it: str, other: str
) -> None:
    assert detect([of_it] * 19 + [other], ()) == {kind: 0.95}
    assert detect([of_it] * 18 + [other] * 2, ()) == {}, "nine values of ten are not"


def test_a_column_of_values_of_countries_and_currencies_alike_is_a_match_of_both() -> None:
    assert detect(["276", "756", "040"], ()) == {
        COUNTRY_NUMBER: 1.0,
        CURRENCY_NUMBER: 1.0,
    }, "Germany and its mark, Switzerland and its franc, Austria and its schilling"
    assert detect(["CHE", "BTN"], ()) == {COUNTRY_ALPHA_3: 1.0, CURRENCY_CODE: 1.0}


@pytest.mark.parametrize(
    ("words", "written"),
    [
        (("true",), ("true", "True", "TRUE")),
        (("US Dollar",), ("US Dollar", "us dollar", "US DOLLAR")),
        (("0",), ("0",)),
        (("yes", "no", "Yes"), ("yes", "Yes", "YES", "no", "No", "NO")),
    ],
    ids=["in lower case", "of capitals", "of no letters", "several"],
)
def test_words_are_written_in_each_of_their_cases_once(
    words: tuple[str, ...], written: tuple[str, ...]
) -> None:
    assert cases(*words) == written


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


def test_only_the_types_of_uuids_and_dates_are_of_no_enumeration(
    account_number: SemanticType,
) -> None:
    none = [kind.name for kind in all_types([account_number]) if not kind.enumerable]
    assert none == [DATE.name, UUID.name], "a column of a type of a project may be one"


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


@pytest.mark.parametrize(
    ("text", "separating"),
    [
        (";", True),
        ("|", True),
        (",", True),
        ("a", False),
        ("1", False),
        ("-", False),
        ("+", False),
        ("_", False),
        (";;", False),
        ("", False),
    ],
    ids=lambda value: repr(value),
)
def test_a_separator_of_lists_is_one_character_that_no_value_of_a_list_holds(
    text: str, separating: bool
) -> None:
    assert is_list_separator(text) is separating


@pytest.mark.parametrize(
    ("texts", "listed"),
    [
        (["12;47;3", "4", "7;12"], True),
        (["a-1;B_2;+3", "x"], True),
        (["4", "7", "12"], False),
        (["12;;47", "4;7"], False),
        (["12;47;", "4;7"], False),
        ([";12", "4;7"], False),
        (["12,47", "4;7"], False),
        (["12; 47", "4;7"], False),
    ],
    ids=[
        "lists",
        "values of letters, digits and signs",
        "single values alone",
        "two separators in a row",
        "a separator at the end",
        "a separator at the start",
        "another separator",
        "a space",
    ],
)
def test_texts_are_lists_where_each_is_one_and_one_holds_several_values(
    texts: list[str], listed: bool
) -> None:
    assert is_list(texts, ";") is listed


def test_a_column_of_lists_is_one_of_nearly_every_text_a_list() -> None:
    assert is_list(["1;2"] * 19 + ["a b"], ";")
    assert not is_list(["1;2"] * 18 + ["a b"] * 2, ";"), "nine texts of ten are not"
