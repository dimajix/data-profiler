"""Tests of the stage report: a profile made by hand, rendered as HTML."""

from pathlib import Path

import pytest

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.profile import (
    Column,
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
                    statistics=Statistics(300, 2, Lengths(1, 2), Range("<b>", None)),
                    values=(Value("<script>alert(1)</script>", 800), Value("B", 100)),
                ),
                Column(
                    name="eml_adr",
                    type="varchar(120)",
                    statistics=Statistics(0, 1150),
                    matches=(Match(SemanticType.EMAIL, 0.982, 0.99),),
                ),
                Column(
                    name="cust_nm",
                    type="varchar(80)",
                    statistics=Statistics(0, 1100),
                    marked=Sensitivity.PERSONAL,
                ),
                Column(
                    name="tel_no",
                    type="varchar(20)",
                    statistics=Statistics(0, 2, range=Range("", "0301234567")),
                    matches=(Match(SemanticType.PHONE, 0.6, 0.6),),
                    marked=Sensitivity.NONE,
                ),
            ),
        ),
        Table(name="empty", rows=0, columns=(Column("x", "bigint", Statistics(0, 0)),)),
    ),
    glossary={"cust": "customer", "typ": "type", "cd": "code"},
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
    assert "<td> 1 … 2 </td>" in page, "the lengths of a text"
    assert "email 98% / 99%" in page, "a match with its shares in the sample and on the table"
    assert '<td class="number"> \u2013 </td>' in page, "no share of nulls of a table without rows"


def test_a_report_shows_the_sensitivity_of_a_column_and_whether_it_is_marked() -> None:
    page = _page()
    assert "5 columns · 2 columns sensitive" in page
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


def test_the_glossary_shows_each_term_with_its_word_and_where_it_appears() -> None:
    page = _page()
    assert '<td class="original">cust</td> <td>customer</td>' in page
    assert '<td class="original">eml</td> <td>—</td> <td> cust.eml_adr </td>' in page


def test_a_report_holds_its_styles_whole_and_no_script() -> None:
    page = render(_PROFILE)
    assert '"Segoe UI"' in page, "the style sheet is not escaped"
    assert "<link" not in page
    assert "<script" not in page


def test_a_report_that_cannot_be_written_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="cannot be written"):
        write_report(_PROFILE, tmp_path / "missing" / "report.html")
