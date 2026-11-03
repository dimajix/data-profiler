"""Tests of the stage report: a profile made by hand, rendered as HTML."""

from pathlib import Path

import pytest

from data_profiler.detect import EMAIL, PHONE, Sensitivity
from data_profiler.profile import (
    Column,
    Concept,
    Group,
    Lengths,
    Match,
    Profile,
    Range,
    Statistics,
    Table,
    Value,
)
from data_profiler.report import ReportError, render, write_report

_PROFILE = Profile(
    catalog="crm",
    schema="sales",
    tables=(
        Table(
            name="cust",
            rows=1200,
            columns=(
                Column(
                    name="cust_typ_cd",
                    type="varchar(2)",
                    statistics=Statistics(
                        300, 2, Lengths(1, 2), Range("<b>", None), (Value("", 40), Value("-", 20))
                    ),
                    values=(Value("<script>alert(1)</script>", 800), Value("B", 100)),
                ),
                Column(
                    name="eml_adr",
                    type="varchar(120)",
                    statistics=Statistics(0, 1150),
                    matches=(Match(EMAIL, 0.982, 0.99),),
                ),
                Column(
                    name="cust_nm",
                    type="varchar(80)",
                    statistics=Statistics(0, 1100),
                    marked=Sensitivity.PERSONAL,
                ),
                Column(name="ap_tel_no", type="varchar(20)", statistics=Statistics(0, 2)),
                Column(name="custtyp", type="varchar(1)", statistics=Statistics(0, 2)),
                Column(
                    name="tel_no",
                    type="varchar(20)",
                    statistics=Statistics(0, 2, range=Range("", "0301234567")),
                    matches=(Match(PHONE, 0.6, 0.6),),
                    marked=Sensitivity.NONE,
                ),
            ),
            groups=(Group(("eml_adr", "tel_no"), 0.947),),
        ),
        Table(
            name="empty",
            rows=0,
            columns=(Column("x", "bigint", Statistics(0, 0)),),
        ),
    ),
    glossary={
        "customer": Concept(("cust",), "A person or company that buys."),
        "type": Concept(("typ",)),
        "code": Concept(("cd",)),
        "airplus": Concept(("ap",), omitted=True),
        "telephone": Concept(("tel",)),
        "number": Concept(("no",)),
        "void": Concept(("empty",)),
        "blank": Concept(("empty",)),
    },
)


def _page() -> str:
    """The report of `_PROFILE`, its white space each one space."""
    return " ".join(render(_PROFILE).split())


def test_a_report_shows_the_tables_and_their_columns() -> None:
    page = _page()
    assert "<h1>crm.sales</h1>" in page
    assert "1,200 rows" in page
    assert "customer_type_code" in page, "the harmonized name of a column"
    assert "25%" in page, "the share of the nulls"
    assert '<td class="number">5%</td>' in page, "the share of the sentinels"
    assert "2 sentinels" in page, "each of the sentinels"
    assert '<span class="value">(empty)</span> 40' in page, "the empty text shown"
    assert "<td> 1 … 2 </td>" in page, "the lengths of a text"
    assert "email 98% / 99%" in page, "a match with its shares in the sample and on the table"
    assert '<td class="number">\u2013</td>' in page, "no share of nulls of a table without rows"


def test_a_report_shows_the_groups_of_columns_filled_together() -> None:
    assert 'Filled together: <span class="original">eml_adr, tel_no</span> (95%)' in _page()


def test_a_report_shows_the_sensitivity_of_a_column_and_whether_it_is_marked() -> None:
    page = _page()
    assert "7 columns · 2 columns sensitive" in page
    assert "personal (marked)" in page
    assert '<span class="sensitivity"> personal </span>' in page, "found by a match, not marked"
    assert page.count('class="sensitive"') == 2, "a column of no sensitivity is not shown as one"
    assert "none (marked)" in page, "a mark of no sensitivity over a sensitive match"


def test_a_range_shows_both_its_ends_and_says_where_one_is_withheld() -> None:
    page = _page()
    assert "&lt;b&gt; … withheld" in page
    assert '<td class="value"> … 0301234567 </td>' in page, "an empty smallest value is one"


def test_the_values_of_the_profile_are_escaped() -> None:
    page = render(_PROFILE)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_the_glossary_shows_each_concept_and_where_the_terms_of_none_appear() -> None:
    page = _page()
    assert (
        '<td>customer</td> <td class="original">cust</td> <td>A person or company that buys.</td>'
        in page
    )
    assert '<td>airplus <span class="omitted">(omitted)</span></td>' in page
    (_, unknown) = page.split("Terms of no concept")
    assert '<td class="original">eml</td> <td> cust.eml_adr </td>' in unknown
    assert '"original">typ<' not in unknown, "a term of a concept"


def test_a_table_of_a_term_of_several_concepts_is_shown_without_a_harmonized_name() -> None:
    assert '<h2> empty <span class="rows">0 rows</span> </h2>' in _page(), "void or blank"


def test_a_harmonized_name_is_composed_of_the_terms_written_together_split() -> None:
    assert "<td>customer_type</td>" in _page(), "of custtyp, by cust and typ of other names"


def test_a_report_shows_the_harmonized_names_two_columns_share() -> None:
    shared = '<span class="original">ap_tel_no, tel_no</span>'
    assert f"Same harmonized name: telephone_number \u2013 {shared}" in _page()


def test_a_report_holds_its_styles_whole_and_no_script() -> None:
    page = render(_PROFILE)
    assert '"Segoe UI"' in page, "the style sheet is not escaped"
    assert "<link" not in page
    assert "<script" not in page


def test_a_report_that_cannot_be_written_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="cannot be written"):
        write_report(_PROFILE, tmp_path / "missing" / "report.html")
