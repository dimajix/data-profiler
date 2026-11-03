"""Tests of the glossary: names split into terms, and harmonized names composed of their words."""

import pytest

from data_profiler.glossary import Glossary, Vocabulary, occurrences, terms
from data_profiler.profile import Column, Concept, Profile, Statistics, Table


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


def _profile(*tables: Table, glossary: dict[str, Concept] | None = None) -> Profile:
    """A profile of `tables`, of the concepts `glossary`."""
    return Profile(catalog="c", schema="s", tables=tables, glossary=glossary or {})


def _table(name: str, *columns: str) -> Table:
    """A table `name` of the columns of the names `columns`."""
    return Table(
        name=name,
        rows=1,
        columns=tuple(Column(column, "varchar(10)", Statistics(0, 1)) for column in columns),
    )


def test_a_term_written_together_is_split_by_the_terms_found_on_their_own() -> None:
    profile = _profile(_table("kd", "kd_lfadr_plz", "lf_datum", "adr_ort"))
    assert Vocabulary.of(profile).split("KD_LFADR_PLZ") == ["kd", "lf", "adr", "plz"]
    assert occurrences(profile)["adr"] == ["kd.kd_lfadr_plz", "kd.adr_ort"]
    assert "lfadr" not in occurrences(profile)


def test_a_term_written_together_is_split_by_the_abbreviations_of_the_concepts() -> None:
    glossary = {"customer": Concept(("kd",)), "number": Concept(("nr",))}
    profile = _profile(_table("kd", "kdnr"), glossary=glossary)
    assert Vocabulary.of(profile).split("kdnr") == ["kd", "nr"], "nr is in no name on its own"


def test_an_abbreviation_of_a_concept_is_never_split() -> None:
    tables = (_table("kd", "kd_lfadr_plz", "lf_datum", "adr_ort"),)
    profile = _profile(*tables, glossary={"delivery_address": Concept(("lfadr",))})
    assert Vocabulary.of(profile).split("KD_LFADR_PLZ") == ["kd", "lfadr", "plz"]


def test_a_term_the_vocabulary_covers_in_part_is_left_whole() -> None:
    vocabulary = Vocabulary.of(_profile(_table("rt", "crt", "tot", "to_dt", "brth")))
    assert [vocabulary.split(name) for name in ("crt", "tot", "brth")] == [
        ["crt"],
        ["tot"],
        ["brth"],
    ], "as no other terms cover them whole, of two characters each"


def test_a_term_is_split_into_the_fewest_terms_the_longer_first() -> None:
    vocabulary = Vocabulary(["abc", "def", "ab", "cd", "ef"], [])
    assert vocabulary.split("abcdef") == ["abc", "def"], "of two, not of ab, cd and ef"
    assert Vocabulary(["abc", "de", "ab", "cde"], []).split("abcde") == ["abc", "de"]
    assert Vocabulary(["a", "bc"], []).split("abc") == ["abc"], "of no part of one character"


def test_each_part_of_a_term_written_together_is_split_again() -> None:
    vocabulary = Vocabulary(["lfadr", "plz", "lf", "adr"], [])
    assert vocabulary.split("lfadrplz") == ["lf", "adr", "plz"]
    assert Vocabulary(["lfadr", "plz", "lf", "adr"], ["lfadr"]).split("lfadrplz") == [
        "lfadr",
        "plz",
    ], "but an abbreviation of a concept"


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
    assert found["cust"][:3] == ["cntct.cust_id", "cust", "cust.cust_id"]
    assert "cust_addr" in found["addr"], "the terms of the names of tables are found as well"
    assert found["iban"] == ["ord.iban"]
    assert list(found)[:4] == ["cntct", "id", "cust", "typ"], "in the order they first appear"
    assert "ord_itm.prodgrp_cd" in found["grp"], "a term written together split"
    vocabulary = Vocabulary.of(example_profile)
    names = [c.name for t in example_profile.tables for c in t.columns]
    split = {name for name in names if vocabulary.split(name) != terms(name)}
    assert split == {"prodgrp_cd"}, "and no abbreviation of a term covered in part"


def _glossary(**concepts: tuple[str, ...]) -> Glossary:
    """The glossary of `concepts`, each word with its abbreviations."""
    return Glossary({word: Concept(abbreviations) for word, abbreviations in concepts.items()})


def test_a_term_stands_for_the_words_of_the_concepts_it_is_an_abbreviation_of() -> None:
    glossary = _glossary(customer=("cust", "kd"), status=("st",), street=("st", "strt"))
    assert glossary.words("kd") == ("customer",)
    assert glossary.words("st") == ("status", "street"), "in the order of the glossary"
    assert glossary.words("nm") == ()


def test_a_harmonized_name_is_composed_of_the_words_of_its_terms() -> None:
    glossary = Glossary(
        {
            "customer": Concept(("cust", "kd")),
            "date of birth": Concept(("brth",)),
            "Address": Concept(("addr",)),
            "e-mail": Concept(("eml",)),
        }
    )
    assert glossary.harmonized(terms("cust_brth")) == "customer_date_of_birth"
    assert glossary.harmonized(terms("KD_ADDR2")) == "customer_address_2", "of either abbreviation"
    assert glossary.harmonized(terms("eml_addr")) == "e_mail_address"
    words = Glossary({"dateOfBirth": Concept(("brth",))})
    assert words.harmonized(terms("brth")) == "date_of_birth"


def test_a_name_of_a_term_of_several_concepts_is_not_composed() -> None:
    glossary = _glossary(status=("st",), street=("st",), code=("cd",))
    assert glossary.harmonized(terms("st_cd")) is None, "while which one it stands for is not known"


def test_a_concept_omitted_is_left_out_of_the_names() -> None:
    glossary = Glossary(
        {
            "airplus": Concept(("ap",), "Marks a custom column of the CRM.", omitted=True),
            "segment": Concept(("seg",)),
            "code": Concept(("cd",)),
        }
    )
    assert glossary.harmonized(terms("ap_seg_cd")) == "segment_code"
    assert glossary.harmonized(terms("ap")) is None, "where no word is left"


def test_no_name_is_composed_while_a_term_has_no_word() -> None:
    glossary = _glossary(customer=("cust",), date=("dt",))
    assert glossary.harmonized(terms("cust_crt_dt")) is None
    assert glossary.harmonized(terms("__")) is None
    assert _glossary(**{" - ": ("x",)}).harmonized(terms("x")) is None, "a word of nothing"


def test_columns_of_the_same_harmonized_name_are_a_collision() -> None:
    glossary = Glossary(
        {"airplus": Concept(("ap",), omitted=True), "status": Concept(("sts", "st"))}
    )
    statistics = Statistics(0, 1)
    columns = (
        Column("ap_sts", "varchar(1)", statistics),
        Column("id", "bigint", statistics),
        Column("st", "varchar(1)", statistics),
    )
    table = Table(name="t", rows=1, columns=columns)
    assert glossary.collisions(table, Vocabulary.of(_profile(table))) == {
        "status": ("ap_sts", "st")
    }, "id has no name"


def test_the_names_of_the_example_are_composed_from_words_given(example_profile: Profile) -> None:
    glossary = Glossary({f"word_{term}": Concept((term,)) for term in occurrences(example_profile)})
    vocabulary = Vocabulary.of(example_profile)
    for table in example_profile.tables:
        for column in table.columns:
            split = vocabulary.split(column.name)
            name = glossary.harmonized(split)
            assert name is not None, column.name
            assert name == "_".join(f"word_{term}" for term in split)
