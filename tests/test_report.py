"""Tests of the stage report: a profile made by hand, rendered as HTML."""

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from data_profiler.detect import CURRENCY_CODE, EMAIL, PHONE, UUID, Sensitivity
from data_profiler.glossary import terms
from data_profiler.overrides import (
    ColumnOverride,
    DiscriminatorOverride,
    EntityOverride,
    Overrides,
    TableOverride,
)
from data_profiler.profile import (
    Column,
    ColumnDependency,
    ColumnGroup,
    Concept,
    Discriminator,
    Entity,
    Findings,
    Lengths,
    Match,
    PrimaryKey,
    Profile,
    Range,
    Reference,
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
                column_groups=(ColumnGroup(("eml_adr", "tel_no"), 0.947),),
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


def _with_first(**changes: Any) -> Profile:
    """`_PROFILE`, its first column with `changes`."""
    (table, *others) = _PROFILE.tables
    first, *columns = table.columns
    changed = replace(table, columns=(replace(first, **changes), *columns))
    return replace(_PROFILE, tables=(changed, *others))


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


def test_a_report_shows_a_column_of_lists_with_its_separator() -> None:
    page = _page(profile=_with_first(list_separator=";"))
    assert "list of values by ;" in page


def test_a_report_shows_the_values_of_the_lists_of_a_column() -> None:
    items = Findings(Statistics(0, 6), matches=(Match(CURRENCY_CODE, 1.0, 1.0),))
    page = _page(profile=_with_first(list_separator=";", items=items))
    assert "list of values by ;: 6 distinct" in page
    assert "currency-code 100% / 100%" in page, "its type, of the sample and of the table"


# Seven UUIDs, the most frequent first.
_UUIDS = tuple(Value(f"00000000-0000-4000-8000-00000000000{n}", 9 - n) for n in range(7))


@pytest.mark.parametrize("verified", [1.0, None])
def test_a_column_of_nothing_but_uuids_lists_its_five_most_frequent_values(
    verified: float | None,
) -> None:
    page = _page(profile=_with_first(values=_UUIDS, matches=(Match(UUID, 1.0, verified),)))
    assert "<summary>5 of 7 values</summary>" in page
    assert _UUIDS[4].value in page, "the fifth most frequent"
    assert _UUIDS[5].value not in page, "the sixth most frequent"


def test_the_values_of_lists_of_nothing_but_uuids_are_limited_by_their_own_matches() -> None:
    items = Findings(Statistics(0, 7), matches=(Match(UUID, 1.0, 1.0),), values=_UUIDS)
    page = _page(profile=_with_first(list_separator=";", items=items))
    assert "<summary>5 of 7 values of its lists</summary>" in page
    assert _UUIDS[5].value not in page, "the sixth most frequent"
    assert "<summary>2 values</summary>" in page, "the values of the column, of other matches"


@pytest.mark.parametrize(("sample", "table"), [(0.95, 0.95), (1.0, 0.95), (0.95, None)])
def test_a_column_partly_of_uuids_lists_all_of_its_values(
    sample: float, table: float | None
) -> None:
    page = _page(profile=_with_first(values=_UUIDS, matches=(Match(UUID, sample, table),)))
    assert "<summary>7 values</summary>" in page
    assert _UUIDS[6].value in page, "the last"


def test_a_column_of_five_uuids_says_nothing_of_a_limit() -> None:
    page = _page(profile=_with_first(values=_UUIDS[:5], matches=(Match(UUID, 1.0, 1.0),)))
    assert "<summary>5 values</summary>" in page


def test_the_sentinels_of_a_column_of_nothing_but_uuids_are_all_listed() -> None:
    statistics = Statistics(0, 7, sentinels=_UUIDS)
    page = _page(profile=_with_first(statistics=statistics, matches=(Match(UUID, 1.0, 1.0),)))
    assert "<summary>7 sentinels</summary>" in page


def test_the_line_below_a_column_runs_below_what_is_listed_of_it() -> None:
    assert "tr:has(+ .values) td { border-bottom: none; }" in _page()


def test_a_report_shows_the_keys_of_a_table_and_which_is_primary() -> None:
    (table, empty) = _PROFILE.tables
    keyed = replace(
        table, keys=(("eml_adr",), ("cust_nm", "tel_no")), primary_key=PrimaryKey(("eml_adr",))
    )
    page = _page(profile=replace(_PROFILE, tables=(keyed, empty)))
    assert (
        'Keys: <span class="original">eml_adr</span> (primary) ·'
        ' <span class="original">cust_nm, tel_no</span> </p>'
    ) in page
    assert page.count('<p class="keys">') == 1, "none of a table of no keys"


def test_a_report_shows_a_primary_key_given_and_whether_it_is_one_of_the_keys() -> None:
    (table, empty) = _PROFILE.tables
    given = PrimaryKey(("cust_nm", "tel_no"), given=True)
    keyed = replace(table, keys=(("cust_nm", "tel_no"),), primary_key=given)
    page = _page(profile=replace(_PROFILE, tables=(keyed, empty)))
    assert '<span class="original">cust_nm, tel_no</span> (primary, given)' in page
    unkeyed = replace(table, keys=(("eml_adr",),), primary_key=given)
    page = _page(profile=replace(_PROFILE, tables=(unkeyed, empty)))
    assert (
        '<span class="original">eml_adr</span> · <span class="original">cust_nm, tel_no</span>'
        " (primary, given; not one of the keys)"
    ) in page


def test_a_report_shows_the_references_of_a_table_its_candidates_and_those_to_it() -> None:
    (table, empty) = _PROFILE.tables
    related = replace(
        table,
        keys=(("eml_adr",),),
        references=(
            Reference("eml_adr", "empty", "x", 1.0),
            Reference("tel_no", "cust", "eml_adr", None, given=True),
        ),
        reference_candidates=(
            Reference("cust_nm", "empty", "x", 0.96),
            Reference("cust_nm", "cust", "eml_adr", 1.0),
        ),
    )
    page = _page(profile=replace(_PROFILE, tables=(related, empty)))
    assert (
        '<td class="original">eml_adr</td> <td class="original">empty</td>'
        ' <td class="original">x</td> <td>one to one</td> <td class="number">100%</td>'
        " <td>\u2013</td>"
    ) in page, "a key refers one to one"
    assert (
        '<td class="original">tel_no</td> <td class="original">cust</td>'
        ' <td class="original">eml_adr</td> <td>many to one</td> <td class="number">\u2013</td>'
        " <td>given</td>"
    ) in page, "unmistakable values of no coverage, given"
    assert (
        'Reference candidates of <span class="original">cust_nm</span>:'
        ' <span class="original">empty.x</span> (96%) ·'
        ' <span class="original">cust.eml_adr</span> (100%) </p>'
    ) in page, "as they are ranked"
    assert (
        "<caption>Referred to by</caption>" in page
        and '<td class="original">cust</td> <td class="original">tel_no</td>'
        ' <td class="original">eml_adr</td> <td>many to one</td>'
        in page
    ), "of the references alone, not the candidates, each with the key referred to"
    assert page.count("<caption>References</caption>") == 1, "none of a table of no references"
    assert page.count("<caption>Referred to by</caption>") == 2, "cust, and empty, referred to"


def _figures(*tables: Table) -> list[str]:
    """The diagrams of a report of `tables`, as they appear in it."""
    profile = replace(_PROFILE, tables=tables)
    return re.findall(r'<figure class="diagram">.*?</figure>', _page(profile=profile))


def _lefts(figure: str, name: str) -> list[int]:
    """The left edges of the boxes of the table `name` in `figure`."""
    return [int(x) for x in re.findall(rf'<a href="#table-{name}"><rect x="(\d+)"', figure)]


def _centre(figure: str) -> int:
    """The left edge of the box of the table in the centre of `figure`."""
    found = re.search(r'<g class="centre"><rect x="(\d+)"', figure)
    assert found, "the box of the table"
    return int(found[1])


_ORD = Table("ord", 10, (Column("cust_ref", "bigint", Statistics(0, 5)),))


def _connected_both_ways() -> list[Table]:
    """`cust` refers to `empty`, `ord` to `cust`, and `cust` by a candidate to `ord`."""
    (cust, empty) = _PROFILE.tables
    cust = replace(
        cust,
        references=(Reference("eml_adr", "empty", "x", 1.0),),
        reference_candidates=(Reference("cust_nm", "ord", "cust_ref", 0.96),),
    )
    return [cust, empty, replace(_ORD, references=(Reference("cust_ref", "cust", "eml_adr", 1.0),))]


def test_a_diagram_shows_those_that_refer_on_the_left_and_those_referred_to_on_the_right() -> None:
    figure = _figures(*_connected_both_ways())[0]
    assert ">cust</text>" in figure
    centre = _centre(figure)
    (coming, going) = _lefts(figure, "ord")
    assert coming < centre < going, "ord on the left by a reference, on the right by a candidate"
    assert _lefts(figure, "empty")[0] > centre


def test_a_diagram_dashes_the_tables_connected_by_reference_candidates_alone() -> None:
    going = _figures(*_connected_both_ways())[0]
    assert going.count('class="line candidate"') == 1, "the candidate going out alone"
    assert going.count('class="line"') == 2
    coming = _figures(*_connected_both_ways())[2]
    assert coming.count('class="line candidate"') == 1, "the candidate coming in"
    assert coming.count('class="line"') == 1


def test_a_report_with_a_diagram_holds_no_script() -> None:
    page = _page(profile=replace(_PROFILE, tables=tuple(_connected_both_ways())))
    assert '<figure class="diagram">' in page
    assert "<script" not in page


def test_a_table_connected_by_a_reference_and_a_candidate_is_connected_by_the_reference() -> None:
    (cust, empty) = _PROFILE.tables
    cust = replace(
        cust,
        references=(Reference("eml_adr", "empty", "x", 1.0),),
        reference_candidates=(Reference("cust_nm", "empty", "x", 0.96),),
    )
    figure = _figures(cust, empty)[0]
    assert figure.count('<a href="#table-empty">') == 1, "one box, however many references"
    assert 'class="line candidate"' not in figure


def test_a_diagram_shows_a_table_connected_to_itself_as_a_loop_and_not_as_a_box() -> None:
    (cust, empty) = _PROFILE.tables
    cust = replace(cust, references=(Reference("tel_no", "cust", "eml_adr", None, given=True),))
    (figure,) = _figures(cust, empty)
    assert "#table-cust" not in figure
    assert figure.count('class="line"') == 1


def test_a_diagram_dashes_the_loop_of_a_table_connected_to_itself_by_a_candidate_alone() -> None:
    (cust, empty) = _PROFILE.tables
    cust = replace(cust, reference_candidates=(Reference("cust_nm", "cust", "eml_adr", 0.96),))
    (figure,) = _figures(cust, empty)
    assert "#table-cust" not in figure
    assert figure.count('class="line candidate"') == 1


def test_a_diagram_shows_the_number_of_the_tables_it_does_not_show() -> None:
    (cust, _) = _PROFILE.tables
    referring = [
        replace(
            _ORD, name=f"t{place:02}", references=(Reference("cust_ref", "cust", "eml_adr", 1.0),)
        )
        for place in range(22)
    ]
    figure = _figures(cust, *referring)[0]
    assert "#table-t19" in figure
    assert "#table-t20" not in figure
    assert '<g class="more">' in figure and ">+ 2 more</text>" in figure


def test_a_diagram_escapes_the_names_it_shows() -> None:
    (cust, _) = _PROFILE.tables
    named = replace(_ORD, name="<b>", references=(Reference("cust_ref", "cust", "eml_adr", 1.0),))
    figure = _figures(cust, named)[0]
    assert ">&lt;b&gt;</text>" in figure
    assert "<b>" not in figure


def test_a_table_connected_to_none_has_no_diagram() -> None:
    assert '<figure class="diagram">' not in _page()


def test_a_report_shows_the_groups_of_columns_filled_together() -> None:
    assert 'Filled together: <span class="original">eml_adr, tel_no</span> (95%)' in _page()


def test_a_report_shows_the_column_dependencies_the_determinant_of_a_reference_marked() -> None:
    (table, empty) = _PROFILE.tables
    dependent = replace(
        table,
        references=(Reference("eml_adr", "empty", "x", 1.0),),
        column_dependencies=(
            ColumnDependency(("eml_adr",), ("tel_no",), 0.968),
            ColumnDependency(("cust_typ_cd", "cust_nm"), (), 1.0),
        ),
    )
    page = _page(profile=replace(_PROFILE, tables=(dependent, empty)))
    assert (
        'Determines: <span class="original">eml_adr</span> (refers to <span class="original">'
        'empty.x</span>) → <span class="original">tel_no</span> (97%)'
    ) in page
    assert ('Determines: <span class="original">cust_typ_cd ⇔ cust_nm</span> (100%)') in page, (
        "equivalent determinants, of no dependent"
    )


def _discriminated(given: tuple[tuple[str, ...], ...] | None = None) -> Profile:
    """`_PROFILE`, its customers of two entities by their type, counted with the values `given`."""
    (table, empty) = _PROFILE.tables
    filled = {column.name: 400 for column in table.columns}
    entities = (
        Entity(("<script>alert(1)</script>",), 800, {**filled, "eml_adr": 800}),
        Entity(("B",), 100, {**filled, "eml_adr": 0, "tel_no": 100}),
    )
    discriminated = replace(table, discriminator=Discriminator("cust_typ_cd", entities, given))
    return replace(_PROFILE, tables=(discriminated, empty))


def test_a_report_shows_the_entities_by_the_share_of_their_rows_each_column_is_filled_in() -> None:
    page = _page(profile=_discriminated())
    assert 'Entities by <span class="original">cust_typ_cd</span>' in page
    assert "300 rows of none" in page, "the rows of no value of the discriminator"
    assert '<span class="value">B</span><br> 100 rows' in page, "each entity by its values"
    assert '<span class="value">&lt;script&gt;' in page, "its values escaped"
    assert (
        '<td class="original">eml_adr</td> <td class="number">100%</td> <td class="number">0%</td>'
    ) in page, "the share of the rows of each entity a column is filled in"


def test_a_report_shows_the_entities_by_the_values_of_lists_without_rows_of_none() -> None:
    profile = _discriminated()
    (table, empty) = profile.tables
    columns = tuple(
        replace(column, list_separator=";", items=Findings(Statistics(0, 2), values=column.values))
        if column.name == "cust_typ_cd"
        else column
        for column in table.columns
    )
    page = _page(profile=replace(profile, tables=(replace(table, columns=columns), empty)))
    assert (
        'Entities by <span class="original">cust_typ_cd</span>, by the values of its lists' in page
    )
    assert "rows of none" not in page, "a row of a list is of each entity of a value of it"


def test_a_report_shows_the_names_and_descriptions_given_of_entities() -> None:
    business = EntityOverride(("B",), "A <i>company</i>.")
    given = DiscriminatorOverride("cust_typ_cd", {"business": business})
    overrides = Overrides(tables={"cust": TableOverride(columns=_MARKED, discriminator=given)})
    page = _page(overrides, _discriminated((("B",),)))
    assert '<span class="harmonized">business</span><br> <span class="value">B</span>' in page
    described = '<span class="harmonized">business</span> \u2013 A &lt;i&gt;company&lt;/i&gt;.'
    assert described in page, "its description escaped"


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
    assert '<td>customer_type_code<span class="reading">' in page
    assert '<td class="original">eml_adr</td> <td>\u2013</td>' in page, "of a name not read"


def test_a_report_shows_the_reading_of_a_table_and_of_a_column() -> None:
    page = _page()
    assert '<span class="original">cust</span> \u2192 customer</span> </h2>' in page, "of a table"
    terms = (
        '<span class="reading"> <span class="original">cust</span> \u2192 customer \u00b7 '
        '<span class="original">typ</span> \u2192 type \u00b7 '
        '<span class="original">cd</span> \u2192 code</span></td>'
    )
    assert terms in page, "of a column"


def test_a_reading_marks_the_concepts_omitted() -> None:
    assert (
        '<span class="original">ap</span> \u2192 airplus <span class="omitted">(omitted)</span>'
        in (_page())
    )


def test_a_reading_is_shown_of_a_name_with_a_word_of_no_concept() -> None:
    glossary = {word: c for word, c in _PROFILE.glossary.items() if word != "type"}
    page = _page(profile=replace(_PROFILE, glossary=glossary))
    assert '<td>\u2013<span class="reading">' in page, "no harmonized name, but its reading"
    assert '<span class="original">typ</span> \u2192 type' in page


@pytest.mark.parametrize("reading", [None, ("customer", "type"), ("customer", "kind", "code")])
def test_a_reading_that_does_not_agree_with_the_terms_of_its_name_is_not_shown(
    reading: tuple[str, ...] | None,
) -> None:
    assert '<span class="original">typ</span> \u2192' not in _page(
        profile=_with_first(reading=reading)
    )


def test_a_term_of_digits_is_read_as_itself() -> None:
    profile = _with_first(terms=(Term("addr", ("address",)), Term("2")), reading=("address", "2"))
    assert '<span class="original">2</span> → 2</span>' in _page(profile=profile)


def test_an_abbreviation_given_that_no_name_has_is_warned_of(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = _page(_overrides(glossary={"order": Concept(("ord",))}))
    assert "<td> order </td>" in page
    assert caplog.messages == [
        "The overrides give abbreviations, in lower case as terms are, that no name of the profile"
        " has: ord"
    ]


def test_a_report_shows_what_the_database_and_a_table_hold_where_it_is_given() -> None:
    given = TableOverride(columns=_MARKED, description="The customers.")
    page = _page(Overrides(description="A CRM.", tables={"cust": given}))
    assert '</h1> <p class="about">A CRM.</p>' in page
    assert '</h2> <p class="about">The customers.</p>' in page
    assert page.count('class="about"') == 2, "not of a table of none given"


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
    assert '<td class="original">tel_no</td> <td>phone<span class="reading">' in page
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
