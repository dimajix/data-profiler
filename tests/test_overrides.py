"""Tests of overrides: read from a document, laid over a profile, refused where they name amiss."""

from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.overrides import ColumnOverride, Overrides, OverridesError, TableOverride
from data_profiler.profile import Column, Profile, Range, Statistics, Table, Value

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
    glossary={"cntct": "contact", "frst": "fist"},
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


def test_the_words_of_the_overrides_are_taken_as_given() -> None:
    laid = Overrides(glossary={"frst": "first", "nm": "name"}).laid_over(_PROFILE)
    assert laid.glossary == {"cntct": "contact", "frst": "first", "nm": "name"}


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        (Overrides(glossary={"CUST": "customer"}), "that no name of the profile has: CUST"),
        (Overrides(tables={"cust": TableOverride()}), "tables that are not profiled: cust"),
        (_marked("lst_nm"), "columns of cntct it does not have: lst_nm"),
    ],
    ids=["a term", "a table", "a column"],
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
    assert overrides.glossary == {"cust": "customer"}
    marked = overrides.tables["cntct"].columns["frst_nm"]
    assert marked == ColumnOverride(sensitivity=Sensitivity.PERSONAL)
    assert overrides.tables["ord"].sentinels == {"dlvr_pst_cd": ("", "00000")}


def test_the_overrides_of_the_example_project_lay_over_its_profile(
    example_profile: Profile,
) -> None:
    laid = Overrides.read(_EXAMPLE).laid_over(example_profile)
    columns = {f"{t.name}.{c.name}": c for t in laid.tables for c in t.columns}
    assert columns["cntct.lst_nm"].sensitivity is Sensitivity.PERSONAL


def test_overrides_of_another_format_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text("format: 1\nglossary: {}\n", encoding="utf-8")
    with pytest.raises(OverridesError, match="format 1, but only format 2"):
        Overrides.read(path)
