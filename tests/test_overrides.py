"""Tests of overrides: read from a document, laid over a profile, refused where they name amiss."""

from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.overrides import ColumnOverride, Overrides, OverridesError, TableOverride
from data_profiler.profile import Column, Concept, Profile, Range, Statistics, Table, Value

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm" / "overrides.yml"

_PROFILE = Profile(
    catalog="crm",
    schema="sales",
    tables=(
        Table(
            name="cntct",
            rows=2,
            columns=(
                Column(
                    name="frst_nm",
                    type="varchar(40)",
                    statistics=Statistics(0, 2, range=Range("Anna", "Otto")),
                    values=(Value("Anna", 1), Value("Otto", 1)),
                ),
                Column(
                    name="cntct_typ_cd",
                    type="varchar(5)",
                    statistics=Statistics(0, 1, range=Range("TEL", "TEL")),
                    values=(Value("TEL", 2),),
                ),
            ),
        ),
    ),
    glossary={
        "contact": Concept(("cntct",)),
        "fist": Concept(("frst",)),
        "type_code": Concept(("typ", "cd")),
    },
)


def _marked(name: str) -> Overrides:
    """Overrides that mark the column `name` of `cntct` as personal data."""
    column = ColumnOverride(sensitivity=Sensitivity.PERSONAL)
    return Overrides(tables={"cntct": TableOverride(columns={name: column})})


def test_a_column_marked_sensitive_loses_its_values() -> None:
    (table,) = _marked("frst_nm").laid_over(_PROFILE).tables
    marked, other = table.columns
    assert marked.sensitivity is Sensitivity.PERSONAL
    assert (marked.statistics.range, marked.values) == (None, ())
    assert other == _PROFILE.tables[0].columns[1], "a column not marked keeps what it has"


def test_a_value_of_a_sensitive_type_of_the_project_is_withheld_where_laid_over(
    account_number: SemanticType,
) -> None:
    (table,) = _PROFILE.tables
    other = replace(table.columns[1], values=(Value("A0123456789", 1), Value("TEL", 1)))
    table = replace(table, columns=(table.columns[0], other))
    profile = replace(_PROFILE, tables=(table,), types=(account_number,))
    (laid,) = _marked("frst_nm").laid_over(profile).tables
    assert laid.columns[1].values == (Value("TEL", 1),), "checked by the types of the profile"


def test_a_mark_no_longer_given_is_taken_off() -> None:
    (table,) = _marked("frst_nm").laid_over(_PROFILE).tables
    profile = replace(_PROFILE, tables=(table,))
    (laid,) = Overrides().laid_over(profile).tables
    assert laid.columns[0].marked is None
    assert laid.columns[0].values == (), "its values are not given back"


def test_a_table_agrees_with_the_overrides_where_its_columns_are_marked_as_given() -> None:
    given = _marked("frst_nm").tables["cntct"]
    (table,) = _PROFILE.tables
    assert not given.agrees_with(table), "a column not marked as given"
    assert given.agrees_with(given.laid_over(table))
    assert not TableOverride().agrees_with(given.laid_over(table)), "a column marked otherwise"
    assert not _marked("lst_nm").tables["cntct"].agrees_with(table), "a column it does not have"


def test_a_table_agrees_with_the_overrides_where_counted_with_the_sentinels_given() -> None:
    given = TableOverride(columns={"frst_nm": ColumnOverride(sentinels=("", "-"))})
    assert given.sentinels == {"frst_nm": ("", "-")}
    (table,) = _PROFILE.tables
    assert not given.agrees_with(table), "counted with those of the tool"
    frst_nm, other = table.columns
    counted = replace(table, columns=(replace(frst_nm, sentinels=("", "-")), other))
    assert given.agrees_with(counted)
    assert not TableOverride().agrees_with(counted), "counted with others than of the tool"


def test_sentinels_given_of_a_column_counted_without_them_are_refused() -> None:
    given = TableOverride(columns={"frst_nm": ColumnOverride(sentinels=("",))})
    (table,) = _PROFILE.tables
    with pytest.raises(OverridesError, match="columns of cntct whose values are no text: frst_nm"):
        given.refuse_uncounted(table)
    frst_nm, other = table.columns
    given.refuse_uncounted(replace(table, columns=(replace(frst_nm, sentinels=("",)), other)))
    with pytest.raises(OverridesError, match="columns of cntct it does not have: lst_nm"):
        _marked("lst_nm").tables["cntct"].refuse_uncounted(table)


def test_each_table_selected_has_what_is_given_of_it() -> None:
    overrides = _marked("frst_nm")
    selected = overrides.selected(["cntct", "cust"])
    assert selected == {"cntct": overrides.tables["cntct"], "cust": TableOverride()}
    with pytest.raises(OverridesError, match="tables that are not profiled: cntct"):
        overrides.selected(["cust"])


def test_the_concepts_of_the_overrides_are_taken_as_given() -> None:
    given = {
        "first": Concept(("frst",), "The first of the names of a person."),
        "type": Concept(("typ",)),
    }
    laid = Overrides(glossary=given).laid_over(_PROFILE)
    assert laid.glossary == {
        **given,
        "contact": Concept(("cntct",)),
        "type_code": Concept(("cd",)),
    }, "the concepts proposed without the abbreviations given, and none without any left"
    replaced = Overrides(glossary={"contact": Concept(("cntct",), "A contact.")}).laid_over(
        _PROFILE
    )
    assert replaced.glossary["contact"] == Concept(("cntct",), "A contact."), "of the same word"
    joined = Overrides(glossary={"type_code": Concept(("cd",), "A code.")}).laid_over(_PROFILE)
    assert joined.glossary["type_code"] == Concept(("cd", "typ"), "A code."), (
        "with the abbreviations proposed of its word beside those given"
    )


def test_an_abbreviation_of_a_term_written_together_is_taken_as_given() -> None:
    (table,) = _PROFILE.tables
    profile = replace(
        _PROFILE,
        tables=(
            replace(table, columns=(*table.columns, replace(table.columns[0], name="frstnm"))),
        ),
    )
    laid = Overrides(glossary={"first_name": Concept(("frstnm",))}).laid_over(profile)
    assert laid.glossary["first_name"] == Concept(("frstnm",)), "not split into frst and nm"


def _read(table: tuple[str, ...] | None, column: tuple[str, ...]) -> Overrides:
    """Overrides that read the name of `cntct` as `table`, and of its `frst_nm` as `column`."""
    given = TableOverride(reading=table, columns={"frst_nm": ColumnOverride(reading=column)})
    return Overrides(glossary={"name": Concept(("nm",))}, tables={"cntct": given})


def test_the_readings_of_the_overrides_are_taken_as_given() -> None:
    (table,) = _read(("contact",), ("fist", "name")).laid_over(_PROFILE).tables
    assert table.reading == ("contact",)
    assert table.columns[0].reading == ("fist", "name")
    assert table.columns[1].reading is None, "a column of no reading given"
    given = _read(("contact",), ("fist", "name")).tables["cntct"]
    assert given.laid_over(_PROFILE.tables[0]) == _PROFILE.tables[0], "not by a scan"


def test_a_reading_given_comes_before_the_one_read() -> None:
    (table,) = _PROFILE.tables
    read = replace(
        table, columns=(replace(table.columns[0], reading=("fist", "nm")), table.columns[1])
    )
    (laid,) = _read(None, ("fist", "name")).laid_over(replace(_PROFILE, tables=(read,))).tables
    assert laid.columns[0].reading == ("fist", "name")


def test_the_names_and_descriptions_of_the_overrides_are_taken_as_given() -> None:
    (table,) = _PROFILE.tables
    described = replace(table.columns[1], description="The kind of a contact.")
    profile = replace(_PROFILE, tables=(replace(table, columns=(table.columns[0], described)),))
    given = TableOverride(
        name="contact",
        columns={"frst_nm": ColumnOverride(name="first_name", description="Its first name.")},
    )
    (laid,) = Overrides(tables={"cntct": given}).laid_over(profile).tables
    first, kind = laid.columns
    assert laid.name_given == "contact"
    assert (first.name_given, first.description) == ("first_name", "Its first name.")
    assert (kind.name_given, kind.description) == (None, "The kind of a contact."), "as proposed"
    assert given.laid_over(table) == table, "not by a scan"


def test_a_name_given_other_than_in_snake_case_is_refused_naming_it() -> None:
    given = TableOverride(columns={"frst_nm": ColumnOverride(name="FirstName")})
    with pytest.raises(OverridesError, match="names of cntct other than in snake_case: frst_nm"):
        Overrides(tables={"cntct": given}).laid_over(_PROFILE)


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        (
            Overrides(glossary={"customer": Concept(("CUST",))}),
            "abbreviations, in lower case as terms are, that no name of the profile has: CUST",
        ),
        (Overrides(tables={"cust": TableOverride()}), "tables that are not profiled: cust"),
        (_marked("lst_nm"), "columns of cntct it does not have: lst_nm"),
        (
            _read(None, ("fist",)),
            "readings of names of cntct that read no concept .*, or not one of each: frst_nm",
        ),
        (
            _read(("contract",), ("fist", "name")),
            "readings of names of cntct that read no concept .*: cntct",
        ),
    ],
    ids=["an abbreviation", "a table", "a column", "a reading too short", "a reading amiss"],
)
def test_an_override_of_what_the_profile_does_not_have_is_refused_naming_it(
    overrides: Overrides, problem: str
) -> None:
    with pytest.raises(OverridesError, match=problem):
        overrides.laid_over(_PROFILE)


def test_there_are_no_overrides_where_there_is_no_file(tmp_path: Path) -> None:
    assert Overrides.read(tmp_path / "overrides.yml") == Overrides()


def test_the_overrides_of_the_example_project_are_read() -> None:
    overrides = Overrides.read(_EXAMPLE)
    assert overrides.glossary["address"].abbreviations == ("addr", "adr")
    assert overrides.glossary["airplus"].omitted
    marked = overrides.tables["cntct"].columns["frst_nm"]
    assert marked == ColumnOverride(sensitivity=Sensitivity.PERSONAL)
    assert overrides.tables["ord"].sentinels == {"dlvr_pst_cd": ("", "00000")}
    assert overrides.tables["cust"].columns["cust_ap_id"].name == "contact_person_id"


def test_the_overrides_of_the_example_project_lay_over_its_profile(
    example_profile: Profile,
) -> None:
    laid = Overrides.read(_EXAMPLE).laid_over(example_profile)
    columns = {f"{t.name}.{c.name}": c for t in laid.tables for c in t.columns}
    assert columns["cntct.lst_nm"].sensitivity is Sensitivity.PERSONAL
    assert laid.glossary["address"].abbreviations == ("addr", "adr")
    assert columns["cust.ap_ap_nm"].reading == ("airplus", "contact_person", "name")


def test_overrides_of_another_format_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text("format: 1\nglossary: {}\n", encoding="utf-8")
    with pytest.raises(OverridesError, match="format 1, but only format 5"):
        Overrides.read(path)
