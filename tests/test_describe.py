"""Tests of the stage describe: the names of a profile split into their terms, and read."""

import re
from dataclasses import replace
from pathlib import Path

from data_profiler.describe import describe
from data_profiler.detect import Sensitivity
from data_profiler.glossary import Glossary, occurrences
from data_profiler.overrides import ColumnOverride, Overrides, TableOverride
from data_profiler.profile import Column, Concept, Profile, Statistics, Table, Term
from data_profiler.scan import scan
from data_profiler.source import Source
from data_profiler.workspace import Workspace

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm" / "overrides.yml"


def _profile(*names: str, glossary: dict[str, Concept] | None = None) -> Profile:
    """A profile of a table `cust` of columns of `names`, of the concepts `glossary`."""
    columns = tuple(Column(name, "varchar(10)", Statistics(0, 1)) for name in names)
    table = Table(name="cust", rows=1, columns=columns)
    return Profile(catalog="crm", schema="sales", tables=(table,), glossary=glossary or {})


# The concepts of the profiles of these tests, of an abbreviation of two among them.
_GLOSSARY = {
    "customer": Concept(("cust",)),
    "status": Concept(("st",)),
    "street": Concept(("st",)),
    "code": Concept(("cd",)),
    "name": Concept(("nm",)),
}


def test_a_name_is_split_into_its_terms_each_with_its_candidates() -> None:
    (table,) = describe(_profile("cust_st_cd", "addr2", glossary=_GLOSSARY), Overrides()).tables
    assert table.terms == (Term("cust", ("customer",)),)
    split, digits = table.columns
    assert split.terms == (
        Term("cust", ("customer",)),
        Term("st", ("status", "street")),
        Term("cd", ("code",)),
    )
    assert digits.terms == (Term("addr"), Term("2")), "a term of no concept, and of digits"


def test_a_name_of_one_candidate_for_each_term_is_read_and_any_other_not() -> None:
    profile = _profile("cust_nm", "cust_st_cd", "cust2", "cust_addr", glossary=_GLOSSARY)
    (table,) = describe(profile, Overrides()).tables
    assert table.reading == ("customer",)
    assert [column.reading for column in table.columns] == [
        ("customer", "name"),
        None,
        ("customer", "2"),
        None,
    ], "a term of two concepts and one of none are not read"


def test_a_reading_that_agrees_with_the_terms_of_its_name_is_kept() -> None:
    (table,) = describe(_profile("st_cd", glossary=_GLOSSARY), Overrides()).tables
    chosen = replace(table.columns[0], reading=("street", "code"))
    profile = replace(_profile(glossary=_GLOSSARY), tables=(replace(table, columns=(chosen,)),))
    (again,) = describe(profile, Overrides()).tables
    assert again.columns[0].reading == ("street", "code"), "as chosen, a split that stayed"
    stale = replace(chosen, reading=("street", "name"))
    profile = replace(profile, tables=(replace(table, columns=(stale,)),))
    (again,) = describe(profile, Overrides()).tables
    assert again.columns[0].reading is None, "a reading that no longer agrees is none"


def test_the_concepts_of_the_overrides_count_but_the_profile_holds_nothing_of_them() -> None:
    given = TableOverride(columns={"cust_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL)})
    overrides = Overrides(glossary={"customer": Concept(("cust",))}, tables={"cust": given})
    profile = _profile("cust_nm", glossary={"name": Concept(("nm",))})
    described = describe(profile, overrides)
    (column,) = described.tables[0].columns
    assert column.reading == ("customer", "name"), "by the concept given"
    assert column.marked is None, "the mark given is laid over by the stage that reads it"
    assert described.glossary == profile.glossary


def test_a_reading_given_counts_once_the_name_is_split() -> None:
    given = TableOverride(
        columns={"cust_st_cd": ColumnOverride(reading=("customer", "status", "code"))}
    )
    overrides = Overrides(tables={"cust": given})
    profile = _profile("cust_st_cd", glossary=_GLOSSARY)
    laid = overrides.laid_over(profile)
    assert Glossary(laid.glossary).harmonized(laid.tables[0].columns[0]) is None, "not split"
    laid = overrides.laid_over(describe(profile, overrides))
    assert Glossary(laid.glossary).harmonized(laid.tables[0].columns[0]) == "customer_status_code"


def test_the_names_of_the_example_are_read_from_words_given(example_profile: Profile) -> None:
    glossary = {f"word_{term}": Concept((term,)) for term in occurrences(example_profile)}
    described = describe(replace(example_profile, glossary=glossary), Overrides())
    words = Glossary(glossary)
    for table in described.tables:
        for column in table.columns:
            assert column.terms is not None, column.name
            expected = "_".join(
                term.text if term.text.isdigit() else f"word_{term.text}" for term in column.terms
            )
            assert words.harmonized(column) == expected, column.name


def test_the_names_of_the_example_are_read_with_its_overrides(example_profile: Profile) -> None:
    overrides = Overrides.read(_EXAMPLE)
    laid = overrides.laid_over(describe(example_profile, overrides))
    glossary = Glossary(laid.glossary)
    columns = {c.name: c for c in laid.tables[1].columns}
    assert laid.tables[1].name == "cust"
    assert glossary.harmonized(columns["ap_ap_nm"]) == "contact_person_name", (
        "a term repeated in two meanings, by the reading given"
    )
    assert glossary.harmonized(columns["cust_ap_id"]) == "customer_contact_person_identifier"
    assert glossary.harmonized(columns["ap_seg_cd"]) == "segment_code", "the prefix omitted"


def test_a_scan_keeps_the_terms_and_readings_describe_filled(
    source: Source, tmp_path: Path
) -> None:
    workspace = Workspace.open(tmp_path / "workspace", "crm", "sales")
    directory = tmp_path / "profile"
    pattern = re.compile("cust")
    scan(source, pattern, workspace, (), Overrides(), directory)
    concepts = {"customer": Concept(("cust",)), "identifier": Concept(("id",))}
    described = describe(Profile.read(directory), Overrides(glossary=concepts))
    described.write(directory)
    scan(source, pattern, workspace, (), Overrides(), directory)
    (table,) = Profile.read(directory).tables
    (before,) = described.tables
    assert table.run != before.run, "counted anew"
    assert (table.terms, table.reading) == (before.terms, before.reading)
    assert [(c.terms, c.reading) for c in table.columns] == [
        (c.terms, c.reading) for c in before.columns
    ]
    assert table.columns[0].reading == ("customer", "identifier"), "of cust_id"
