"""Tests of overrides: read from a document, laid over a profile, refused where they name amiss."""

from pathlib import Path

import pytest

from data_profiler.detect import Sensitivity
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


def test_the_words_of_the_overrides_are_taken_as_given() -> None:
    laid = Overrides(glossary={"frst": "first", "nm": "name"}).laid_over(_PROFILE)
    assert laid.glossary == {"cntct": "contact", "frst": "first", "nm": "name"}


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        (Overrides(glossary={"CUST": "customer"}), "that no name of the profile has: CUST"),
        (Overrides(tables={"cust": TableOverride()}), "tables the profile does not have: cust"),
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


def test_the_overrides_of_the_example_project_lay_over_its_profile(
    example_profile: Profile,
) -> None:
    laid = Overrides.read(_EXAMPLE).laid_over(example_profile)
    columns = {f"{t.name}.{c.name}": c for t in laid.tables for c in t.columns}
    assert columns["cntct.lst_nm"].sensitivity is Sensitivity.PERSONAL


def test_overrides_of_another_format_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text("format: 2\nglossary: {}\n", encoding="utf-8")
    with pytest.raises(OverridesError, match="format 2, but only format 1"):
        Overrides.read(path)
