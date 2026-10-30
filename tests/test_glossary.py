"""Tests of the glossary: names split into terms, and harmonized names composed of their words."""

import pytest

from data_profiler.glossary import harmonized, occurrences, terms
from data_profiler.profile import Column, Profile, Statistics, Table


@pytest.mark.parametrize(
    ("name", "found"),
    [
        ("CUST_CRT_DT", ["cust", "crt", "dt"]),
        ("cust_crt_dt", ["cust", "crt", "dt"]),
        ("custCrtDt", ["cust", "crt", "dt"]),
        ("CUSTCrtDt", ["cust", "crt", "dt"]),
        ("addr2", ["addr", "2"]),
        ("cust-addr id", ["cust", "addr", "id"]),
        ("__vld_frm__", ["vld", "frm"]),
        ("ÄndDt", ["änd", "dt"]),
        ("IBAN", ["iban"]),
        ("A\u0308ndDt", ["änd", "dt"]),
        ("", []),
    ],
)
def test_a_name_is_split_into_its_terms(name: str, found: list[str]) -> None:
    assert terms(name) == found


def test_each_term_is_found_with_the_names_it_appears_in_each_once() -> None:
    column = Column(name="ord_ord_no", type="bigint", statistics=Statistics(0, 1))
    profile = Profile(
        catalog="c", schema="s", tables=(Table(name="ord", rows=1, columns=(column,)),)
    )
    assert occurrences(profile) == {"ord": ["ord", "ord.ord_ord_no"], "no": ["ord.ord_ord_no"]}


def test_a_term_of_digits_needs_no_word_and_is_not_found() -> None:
    column = Column(name="addr2", type="varchar(80)", statistics=Statistics(0, 1))
    profile = Profile(
        catalog="c", schema="s", tables=(Table(name="cust", rows=1, columns=(column,)),)
    )
    assert occurrences(profile) == {"cust": ["cust"], "addr": ["cust.addr2"]}


def test_the_terms_of_the_example_are_found_with_their_tables_and_columns(
    example_profile: Profile,
) -> None:
    found = occurrences(example_profile)
    assert found["cust"][:3] == ["cust", "cust.cust_id", "cust.cust_no"]
    assert "cust_addr" in found["addr"], "the terms of the names of tables are found as well"
    assert found["iban"] == ["ord.iban"]
    assert list(found)[:4] == ["cust", "id", "no", "nm"], "in the order they first appear"


def test_a_harmonized_name_is_composed_of_the_words_of_its_terms() -> None:
    glossary = {"cust": "customer", "brth": "date of birth", "addr": "Address", "eml": "e-mail"}
    assert harmonized("cust_brth", glossary) == "customer_date_of_birth"
    assert harmonized("cust_brth", {**glossary, "brth": "dateOfBirth"}) == "customer_date_of_birth"
    assert harmonized("CUST_ADDR2", glossary) == "customer_address_2"
    assert harmonized("eml_addr", glossary) == "e_mail_address"


def test_no_name_is_composed_while_a_term_has_no_word() -> None:
    assert harmonized("cust_crt_dt", {"cust": "customer", "dt": "date"}) is None
    assert harmonized("__", {}) is None
    assert harmonized("cust_x", {"cust": "customer", "x": " - "}) is None, "a word of nothing"


def test_the_names_of_the_example_are_composed_from_words_given(example_profile: Profile) -> None:
    words = {term: f"word_{term}" for term in occurrences(example_profile)}
    for table in example_profile.tables:
        for column in table.columns:
            name = harmonized(column.name, words)
            assert name is not None, column.name
            assert name == "_".join(f"word_{term}" for term in terms(column.name))
