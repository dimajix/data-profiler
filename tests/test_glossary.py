"""Tests of the glossary: names split into terms, and harmonized names composed of their words."""

from dataclasses import replace

import pytest

from data_profiler.glossary import Glossary, Vocabulary, agrees, occurrences, terms, unknown
from data_profiler.profile import Column, Concept, Profile, Statistics, Table, Term


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


def test_the_terms_of_no_concept_are_those_of_no_candidates_as_the_names_were_split() -> None:
    split = (Term("cust", ("customer",)), Term("xy"), Term("2"), Term("xy"))
    columns = (
        Column("cust_xy2xy", "varchar(10)", Statistics(0, 1), terms=split),
        Column("xy_nm", "varchar(10)", Statistics(0, 1), terms=(Term("xy"), Term("nm"))),
        Column("ab_cd", "varchar(10)", Statistics(0, 1)),
    )
    profile = _profile(Table(name="cust", rows=1, columns=columns, terms=(split[0],)))
    assert unknown(profile) == {
        "xy": ["cust.cust_xy2xy", "cust.xy_nm"],
        "nm": ["cust.xy_nm"],
    }, "but of digits, and of a name not split"


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


def _named(*read: tuple[str, str]) -> Column:
    """A column of a name of the terms of `read`, each read as the word beside it, its candidate."""
    terms = tuple(Term(text) if text.isdigit() else Term(text, (word,)) for text, word in read)
    name = "_".join(text for text, _ in read)
    reading = tuple(word for _, word in read)
    return Column(name, "varchar(10)", Statistics(0, 1), terms=terms, reading=reading)


def test_a_harmonized_name_is_composed_of_the_words_of_its_reading() -> None:
    glossary = Glossary(
        {
            "customer": Concept(("cust", "kd")),
            "date of birth": Concept(("brth",)),
            "Address": Concept(("addr",)),
            "e-mail": Concept(("eml",)),
        }
    )
    assert glossary.harmonized(_named(("cust", "customer"), ("brth", "date of birth"))) == (
        "customer_date_of_birth"
    )
    assert glossary.harmonized(_named(("kd", "customer"), ("addr", "Address"), ("2", "2"))) == (
        "customer_address_2"
    ), "of either abbreviation, and the digits of a term of digits"
    assert glossary.harmonized(_named(("eml", "e-mail"), ("addr", "Address"))) == "e_mail_address"
    words = Glossary({"dateOfBirth": Concept(("brth",))})
    assert words.harmonized(_named(("brth", "dateOfBirth"))) == "date_of_birth"


def test_a_reading_agrees_with_its_terms_where_each_word_is_a_candidate_of_its_term() -> None:
    terms = (Term("st", ("status", "street")), Term("cd", ("code",)), Term("2"))
    assert agrees(terms, ("street", "code", "2"))
    assert not agrees(terms, ("code", "code", "2")), "a word of no candidate"
    assert not agrees(terms, ("street", "code")), "of another length"
    assert not agrees(terms, ("street", "code", "3")), "other digits"
    assert not agrees(terms, None)
    assert not agrees(None, ("street", "code", "2"))


def test_a_name_of_no_reading_that_agrees_with_its_terms_has_no_harmonized_name() -> None:
    glossary = _glossary(status=("st",), street=("st",), code=("cd",))
    named = _named(("st", "status"), ("cd", "code"))
    assert glossary.harmonized(named) == "status_code"
    assert glossary.harmonized(replace(named, reading=None)) is None, "not read"
    assert glossary.harmonized(replace(named, terms=None)) is None, "not split"
    assert glossary.harmonized(replace(named, reading=("street", "code"))) is None, (
        "no longer of the candidates of its terms"
    )


def test_a_concept_omitted_is_left_out_of_the_names() -> None:
    glossary = Glossary(
        {
            "airplus": Concept(("ap",), "Marks a custom column of the CRM.", omitted=True),
            "segment": Concept(("seg",)),
            "code": Concept(("cd",)),
        }
    )
    named = _named(("ap", "airplus"), ("seg", "segment"), ("cd", "code"))
    assert glossary.harmonized(named) == "segment_code"
    assert glossary.harmonized(_named(("ap", "airplus"))) is None, "where no word is left"


def test_no_name_is_composed_of_a_word_of_no_concept_or_of_nothing() -> None:
    glossary = _glossary(customer=("cust",), **{" - ": ("x",)})
    assert glossary.harmonized(_named(("cust", "customer"), ("dt", "date"))) is None
    assert glossary.harmonized(_named(("x", " - "))) is None, "a word of nothing"


def test_columns_of_the_same_harmonized_name_are_a_collision() -> None:
    glossary = Glossary(
        {"airplus": Concept(("ap",), omitted=True), "status": Concept(("sts", "st"))}
    )
    columns = (
        _named(("ap", "airplus"), ("sts", "status")),
        Column("id", "bigint", Statistics(0, 1)),
        _named(("st", "status")),
    )
    table = Table(name="t", rows=1, columns=columns)
    assert glossary.collisions(table) == {"status": ("ap_sts", "st")}, "id has no name"
