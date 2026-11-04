"""Tests of the stage report: a profile made by hand, rendered as HTML."""

from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.detect import EMAIL, PHONE, Sensitivity
from data_profiler.glossary import terms
from data_profiler.overrides import ColumnOverride, Overrides, TableOverride
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
    Term,
    Value,
)
from data_profiler.report import ReportError, render, write_report


def _read[Named: (Table, Column)](named: Named, *words: str) -> Named:
    """`named`, its name split into terms of one candidate each, `words`, and read by them."""
    split = zip(terms(named.name), words, strict=True)
    return replace(named, terms=tuple(Term(text, (word,)) for text, word in split), reading=words)


_PROFILE = Profile(
    catalog="crm",
    schema="sales",
    tables=(
        _read(
            Table(
                name="cust",
                rows=1200,
                columns=(
                    _read(
                        Column(
                            name="cust_typ_cd",
                            type="varchar(2)",
                            statistics=Statistics(
                                300,
                                2,
                                Lengths(1, 2),
                                Range("<b>", None),
                                (Value("", 40), Value("-", 20)),
                            ),
                            values=(Value("<script>alert(1)</script>", 800), Value("B", 100)),
                        ),
                        "customer",
                        "type",
                        "code",
                    ),
                    Column(
                        name="eml_adr",
                        type="varchar(120)",
                        statistics=Statistics(0, 1150),
                        matches=(Match(EMAIL, 0.982, 0.99),),
                        terms=(Term("eml"), Term("adr")),
                    ),
                    Column(
                        name="cust_nm",
                        type="varchar(80)",
                        statistics=Statistics(0, 1100),
                        marked=Sensitivity.PERSONAL,
                    ),
                    _read(
                        Column(name="ap_tel_no", type="varchar(20)", statistics=Statistics(0, 2)),
                        "airplus",
                        "telephone",
                        "number",
                    ),
                    _read(
                        Column(
                            name="tel_no",
                            type="varchar(20)",
                            statistics=Statistics(0, 2, range=Range("", "zzz")),
                            matches=(Match(PHONE, 0.6, 0.6),),
                            marked=Sensitivity.NONE,
                        ),
                        "telephone",
                        "number",
                    ),
                ),
                groups=(Group(("eml_adr", "tel_no"), 0.947),),
            ),
            "customer",
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
    },
)


# The marks of the columns of `_PROFILE`, as the overrides of its project give them.
_MARKED = {
    "cust_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL),
    "tel_no": ColumnOverride(sensitivity=Sensitivity.NONE),
}


def _overrides(
    columns: dict[str, ColumnOverride] | None = None,
    name: str | None = None,
    glossary: dict[str, Concept] | None = None,
) -> Overrides:
    """The overrides of `_PROFILE`: its marks, what `columns` gives, `name` and `glossary`."""
    given = TableOverride(columns={**_MARKED, **(columns or {})}, name=name)
    return Overrides(glossary=glossary or {}, tables={"cust": given})


def _page(overrides: Overrides | None = None, profile: Profile = _PROFILE) -> str:
    """The report of `profile`, with `overrides` laid over it, its white space each one space."""
    return " ".join(render(profile, overrides or _overrides()).split())


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
    assert "6 columns · 2 columns sensitive" in page
    assert "personal (marked)" in page
    assert '<span class="sensitivity"> personal </span>' in page, "found by a match, not marked"
    assert page.count('class="sensitive"') == 2, "a column of no sensitivity is not shown as one"
    assert "none (marked)" in page, "a mark of no sensitivity over a sensitive match"


def test_a_range_shows_both_its_ends_and_says_where_one_is_withheld() -> None:
    page = _page()
    assert "&lt;b&gt; … withheld" in page
    assert '<td class="value"> … zzz </td>' in page, "an empty smallest value is one"


def test_the_values_of_the_profile_are_escaped() -> None:
    page = _page()
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_the_glossary_shows_each_concept_and_where_the_terms_of_none_appear() -> None:
    page = _page()
    proposed = '<span class="proposed">(proposed)</span>'
    assert (
        f'<td> customer {proposed} </td> <td class="original">cust</td>'
        " <td>A person or company that buys.</td>" in page
    )
    assert f'<td> airplus <span class="omitted">(omitted)</span> {proposed} </td>' in page
    (_, unknown) = page.split("Terms of no concept")
    assert '<td class="original">eml</td> <td> cust.eml_adr </td>' in unknown
    assert '"original">typ<' not in unknown, "a term of a concept"
    assert '"original">nm<' not in unknown, "a term of a name not split"


def test_a_harmonized_name_is_composed_of_the_reading_of_its_name() -> None:
    page = _page()
    assert '<span class="harmonized">→ customer</span>' in page, "of a table"
    assert "<td>customer_type_code</td>" in page
    assert '<td class="original">eml_adr</td> <td>\u2013</td>' in page, "of a name not read"


def test_an_abbreviation_given_that_no_name_has_is_warned_of(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = _page(_overrides(glossary={"order": Concept(("ord",))}))
    assert "<td> order </td>" in page
    assert caplog.messages == [
        "The overrides give abbreviations, in lower case as terms are, that no name of the profile"
        " has: ord"
    ]


def test_a_concept_given_is_told_apart_from_those_proposed() -> None:
    given = {"customer": Concept(("cust",), "Who buys."), "name": Concept(())}
    page = _page(_overrides(glossary=given))
    assert '<td> customer </td> <td class="original">cust</td> <td>Who buys.</td>' in page
    assert '<td> name </td> <td class="original">\u2013</td>' in page, "of no abbreviations"
    assert '<td> type <span class="proposed">(proposed)</span> </td>' in page


def test_a_report_shows_the_descriptions_given_and_proposed() -> None:
    (table, empty) = _PROFILE.tables
    described = replace(table.columns[0], description="The kind of the customer.")
    profile = replace(
        _PROFILE, tables=(replace(table, columns=(described, *table.columns[1:])), empty)
    )
    given = {"tel_no": ColumnOverride(sensitivity=Sensitivity.NONE, description="Where one calls.")}
    page = _page(_overrides(given), profile)
    assert '<td class="description">The kind of the customer.</td>' in page, "proposed"
    assert '<td class="description">Where one calls.</td>' in page, "given"


def test_a_name_given_comes_before_the_harmonized_name_and_resolves_a_collision() -> None:
    given = {"tel_no": ColumnOverride(sensitivity=Sensitivity.NONE, name="phone")}
    page = _page(_overrides(given, name="client"))
    assert '<span class="harmonized">→ client</span>' in page
    assert '<td class="original">tel_no</td> <td>phone</td>' in page
    assert "Same harmonized name" not in page


def test_a_report_shows_the_harmonized_names_two_columns_share() -> None:
    shared = '<span class="original">ap_tel_no, tel_no</span>'
    assert f"Same harmonized name: telephone_number \u2013 {shared}" in _page()


def test_a_report_holds_its_styles_whole_and_no_script() -> None:
    page = render(_PROFILE, Overrides())
    assert '"Segoe UI"' in page, "the style sheet is not escaped"
    assert "<link" not in page
    assert "<script" not in page


def test_a_report_that_cannot_be_written_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="cannot be written"):
        write_report(_PROFILE, Overrides(), tmp_path / "missing" / "report.html")
