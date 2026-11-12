"""Tests of overrides: read from a document, laid over a profile, refused where they name amiss."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.glossary import Glossary, Vocabulary
from data_profiler.overrides import (
    FORMAT,
    ColumnOverride,
    DiscriminatorOverride,
    EntityOverride,
    GivenReference,
    Overrides,
    OverridesError,
    ReferenceOverride,
    TableOverride,
)
from data_profiler.profile import (
    Column,
    ColumnDependency,
    Concept,
    Discriminator,
    Entity,
    PrimaryKey,
    Profile,
    Range,
    Reference,
    Statistics,
    Table,
    Value,
)

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


def test_sentinels_given_of_a_column_counted_without_them_are_refused_naming_them() -> None:
    given = TableOverride(columns={"frst_nm": ColumnOverride(sentinels=("", "-1"))})
    (table,) = _PROFILE.tables
    frst_nm, other = table.columns
    with pytest.raises(OverridesError, match="cannot hold") as refused:
        given.refuse_uncounted(replace(table, columns=(replace(frst_nm, sentinels=("",)), other)))
    assert str(refused.value).endswith(f'otherwise: frst_nm ({frst_nm.type}): "-1"')
    with pytest.raises(OverridesError, match=r'frst_nm \(.*\): "", "-1"$'):
        given.refuse_uncounted(replace(table, columns=(replace(frst_nm, sentinels=()), other)))
    given.refuse_uncounted(replace(table, columns=(replace(frst_nm, sentinels=("", "-1")), other)))
    empty = TableOverride(columns={"frst_nm": ColumnOverride(sentinels=())})
    empty.refuse_uncounted(replace(table, columns=(replace(frst_nm, sentinels=()), other)))
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


def test_the_word_of_a_concept_given_is_taken_from_the_concepts_proposed() -> None:
    proposed = {**_PROFILE.glossary, "label": Concept(("name",)), "first": Concept(())}
    laid = Overrides(glossary={"name": Concept(())}).laid_over(replace(_PROFILE, glossary=proposed))
    assert "label" not in laid.glossary, "left without any abbreviation"
    assert laid.glossary["name"] == Concept(()), "though no name has its word"
    assert laid.glossary["first"] == Concept(()), "a concept proposed of its word alone is kept"


def test_a_term_given_that_is_the_word_of_a_concept_proposed_stands_for_either() -> None:
    (table,) = _PROFILE.tables
    column = replace(table.columns[1], name="contact_cd")
    profile = replace(_PROFILE, tables=(replace(table, columns=(*table.columns, column)),))
    laid = Overrides(glossary={"person": Concept(("contact",))}).laid_over(profile)
    assert laid.glossary["contact"] == Concept(("cntct",)), "kept, and written as its word"
    assert Glossary(laid.glossary).words("contact") == ("person", "contact")


@pytest.mark.parametrize(
    "proposed",
    [Concept(()), Concept(("iban",))],
    ids=["of its word alone", "its word as an abbreviation, as profiles written before hold it"],
)
def test_a_term_given_that_is_all_a_concept_proposed_is_written_as_stands_for_the_given_alone(
    proposed: Concept,
) -> None:
    profile = replace(_PROFILE, glossary={**_PROFILE.glossary, "iban": proposed})
    laid = Overrides(glossary={"account": Concept(("iban",))}).laid_over(profile)
    assert "iban" not in laid.glossary
    assert Glossary(laid.glossary).words("iban") == ("account",)


def test_a_word_of_several_terms_given_is_a_term_taken_from_the_concepts_proposed() -> None:
    profile = replace(_PROFILE, glossary={"contact": Concept(("contact_person",))})
    overrides = Overrides(glossary={"contact_person": Concept()})
    laid = overrides.laid_over(profile)
    assert "contact" not in laid.glossary
    assert Glossary(laid.glossary).words("contact_person") == ("contact_person",)
    assert overrides.adoptable("contact_person", Concept(("contact_person", "ap"))) == Concept(
        ("ap",)
    ), "not what it is written as by its word"


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


@pytest.mark.parametrize(
    ("given", "word", "proposed", "adoptable"),
    [
        ({}, "contact", Concept(("cntct",), "A."), Concept(("cntct",), "A.")),
        ({}, "contact", Concept((), "A."), Concept((), "A.")),
        ({}, "iban", Concept(("iban",), "A."), Concept((), "A.")),
        ({"contact": Concept(("cntct",))}, "contact", Concept(("cntct",), "A."), Concept((), "A.")),
        ({"contact": Concept((), "B.")}, "contact", Concept(("c",), "A."), Concept(("c",))),
        ({"contact": Concept(("c",), "B.")}, "contact", Concept(("c",), "A."), Concept()),
        ({"contact": Concept(("c", "d"), "B.")}, "contact", Concept(("c",), "A."), Concept()),
        ({"customer": Concept(("c",))}, "contact", Concept(("c",), "A."), Concept()),
        ({"customer": Concept(("c",))}, "contact", Concept(("c", "d")), Concept(("d",))),
        ({"account": Concept(("iban",))}, "iban", Concept((), "A."), Concept()),
    ],
    ids=[
        "a concept of no word given",
        "one of no abbreviations",
        "its word no abbreviation of it",
        "one given without a description",
        "new abbreviations of one given",
        "one given as proposed",
        "one given of more",
        "abbreviations taken by another",
        "those left of them",
        "its word taken by another, of no abbreviations",
    ],
)
def test_what_a_concept_proposed_adds_to_those_given(
    given: dict[str, Concept], word: str, proposed: Concept, adoptable: Concept
) -> None:
    assert Overrides(glossary=given).adoptable(word, proposed) == adoptable


def test_a_field_of_overrides_that_cannot_be_set_is_refused_as_overrides(tmp_path: Path) -> None:
    file = tmp_path / "overrides.yml"
    file.write_text("glossary: {}\n", encoding="utf-8")
    with pytest.raises(OverridesError, match=r"overrides\.yml"):
        Overrides.amend([file], ("glossary", "customer", "description"), "A.", file)


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


def test_a_word_proposed_of_the_pieces_of_a_word_given_is_that_word() -> None:
    profile = replace(_PROFILE, glossary={"b_2_b": Concept(("bb",))})
    laid = Overrides(glossary={"b2b": Concept()}).laid_over(profile)
    assert laid.glossary == {"b2b": Concept(("bb",))}, "the word as it is given"
    assert Vocabulary.of(laid).split("b2b_flag") == ["b2b", "flag"]


def test_a_name_given_of_digits_among_its_letters_is_in_snake_case() -> None:
    given = TableOverride(columns={"frst_nm": ColumnOverride(name="b2b_name")})
    laid = Overrides(tables={"cntct": given}).laid_over(_PROFILE)
    assert laid.tables[0].columns[0].name_given == "b2b_name"


def test_a_name_given_other_than_in_snake_case_is_refused_naming_it() -> None:
    given = TableOverride(columns={"frst_nm": ColumnOverride(name="FirstName")})
    with pytest.raises(OverridesError, match="names of cntct other than in snake_case: frst_nm"):
        Overrides(tables={"cntct": given}).laid_over(_PROFILE)


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
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
    ids=["a table", "a column", "a reading too short", "a reading amiss"],
)
def test_an_override_of_what_the_profile_does_not_have_is_refused_naming_it(
    overrides: Overrides, problem: str
) -> None:
    with pytest.raises(OverridesError, match=problem):
        overrides.laid_over(_PROFILE)


def test_an_abbreviation_given_that_no_name_has_is_warned_of_and_laid_over(
    caplog: pytest.LogCaptureFixture,
) -> None:
    given = {"customer": Concept(("CUST", "kd")), "contact": Concept(("cntct",)), "type": Concept()}
    overrides = Overrides(glossary=given)
    overrides.warn_unused(_PROFILE)
    assert caplog.messages == [
        "The overrides give abbreviations, in lower case as terms are, that no name of the profile"
        " has: CUST, kd"
    ], "not the word of a concept given"
    assert overrides.laid_over(_PROFILE).glossary["customer"] == given["customer"]


def _discriminated(given: tuple[tuple[str, ...], ...] | None = None) -> Table:
    """The table of `_PROFILE`, its contacts by telephone or by fax, and by e-mail.

    Its discriminator is counted with the values `given` of entities, or found where None.
    """
    (table,) = _PROFILE.tables
    frst_nm, kind = table.columns
    kinds = (Value("TEL", 2), Value("EML", 1), Value("FAX", 1))
    entities = (
        Entity(("TEL", "FAX"), 3, {"frst_nm": 3, "cntct_typ_cd": 3}),
        Entity(("EML",), 1, {"frst_nm": 0, "cntct_typ_cd": 1}),
    )
    return replace(
        table,
        rows=4,
        columns=(frst_nm, replace(kind, values=kinds)),
        discriminator=Discriminator("cntct_typ_cd", entities, given),
    )


def _entities(column: str = "cntct_typ_cd", **entities: tuple[str, ...]) -> TableOverride:
    """What gives the discriminator `column` of `cntct`, of entities of the values given."""
    given = {name: EntityOverride(values) for name, values in entities.items()}
    return TableOverride(discriminator=DiscriminatorOverride(column, given))


def _laid(given: TableOverride, table: Table) -> Table:
    """`table`, in the profile of its own, with `given` laid over it by a stage that reads it."""
    (laid,) = (
        Overrides(tables={"cntct": given}).laid_over(replace(_PROFILE, tables=(table,))).tables
    )
    return laid


def test_the_entities_given_are_named_and_described_where_their_values_are() -> None:
    phone = EntityOverride(("TEL",), "A contact by telephone.")
    given = TableOverride(discriminator=DiscriminatorOverride("cntct_typ_cd", {"phone": phone}))
    table = _discriminated((("TEL",),))
    laid = _laid(given, table)
    assert laid.discriminator is not None
    by_phone, by_mail = laid.discriminator.entities
    assert (by_phone.name_given, by_phone.description) == ("phone", "A contact by telephone.")
    assert (by_mail.name_given, by_mail.description) == (None, None), "an entity of none given"
    assert given.laid_over(table) == table, "not by a scan"


@pytest.mark.parametrize(
    ("given", "counted"),
    [
        (_entities(phone=("TEL",)), None),
        (_entities(phone=("TEL",)), (("TEL",), ("FAX",))),
        (_entities("frst_nm", anna=("Anna",)), (("Anna",),)),
    ],
    ids=["found", "counted with others", "another column"],
)
def test_no_names_are_laid_over_entities_of_a_discriminator_counted_otherwise_than_given(
    given: TableOverride, counted: tuple[tuple[str, ...], ...] | None
) -> None:
    table = _discriminated(counted)
    assert _laid(given, table).discriminator == table.discriminator, "until a scan counts it so"


def test_a_table_agrees_with_the_overrides_where_it_was_discriminated_as_given() -> None:
    found = _discriminated()
    counted = _discriminated((("TEL",), ("EML",)))
    assert TableOverride().agrees_with(found), "none given, whatever is found"
    assert not TableOverride().agrees_with(counted), "counted with entities no longer given"
    assert not TableOverride(discriminator=False).agrees_with(found)
    assert TableOverride(discriminator=False).agrees_with(replace(found, discriminator=None))
    assert _entities(phone=("TEL",), mail=("EML",)).agrees_with(counted)
    assert not _entities(mail=("EML",), phone=("TEL",)).agrees_with(counted), "in another order"
    assert not _entities(phone=("TEL",), mail=("EML",)).agrees_with(found)
    assert _entities().agrees_with(_discriminated(())), "of no entity given"
    assert not _entities().agrees_with(replace(found, discriminator=None))


def test_a_table_discriminated_as_given_is_refused_where_its_discriminator_cannot_be_one() -> None:
    table = _discriminated()
    given = replace(
        _entities("frst_nm"), columns={"frst_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL)}
    )
    counted = replace(table, discriminator=Discriminator("frst_nm", (), ()))
    with pytest.raises(OverridesError, match="as frst_nm, a column they mark of a sensitivity"):
        given.agrees_with(counted)


@pytest.mark.parametrize(
    ("given", "problem"),
    [
        (_entities("kind"), "columns of cntct it does not have: kind"),
        (
            replace(
                _entities("frst_nm"),
                columns={"frst_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL)},
            ),
            "discriminator of cntct as frst_nm, a column they mark of a sensitivity",
        ),
        (_entities(phone=("TEL",), fax=("FAX", "TEL")), "a value of it twice among its entities"),
        (_entities(phone=(), fax=(), mail=("EML",)), "and entities of no values: phone, fax"),
        (_entities(Phone=("TEL",)), "names of cntct other than in snake_case: Phone"),
    ],
    ids=["a column missing", "a column sensitive", "a value twice", "no values", "a name"],
)
def test_a_discriminator_given_that_cannot_be_one_is_refused(
    given: TableOverride, problem: str
) -> None:
    with pytest.raises(OverridesError, match=problem):
        _laid(given, _discriminated())


def test_a_discriminator_given_of_values_the_profile_does_not_hold_is_no_mistake() -> None:
    table = _discriminated((("PAGER",),))
    frst_nm, kind = table.columns
    unvalued = replace(table, columns=(frst_nm, replace(kind, values=())))
    given = _entities(pager=("PAGER",))
    assert _laid(given, unvalued).discriminator is None, "dropped with the values, not refused"


def test_a_table_counted_with_a_discriminator_given_of_no_values_held_agrees_unwarned(
    caplog: pytest.LogCaptureFixture,
) -> None:
    given = _entities(pager=("PAGER",))
    (table,) = _PROFILE.tables
    counted = replace(table, discriminator=Discriminator("cntct_typ_cd", (), (("PAGER",),)))
    assert given.agrees_with(counted), "counted with it, of an environment of no pagers"
    Overrides(tables={"cntct": given}).warn_unused(replace(_PROFILE, tables=(counted,)))
    assert caplog.messages == []


def test_a_discriminator_given_otherwise_than_counted_is_warned_of(
    caplog: pytest.LogCaptureFixture,
) -> None:
    profile = replace(_PROFILE, tables=(_discriminated(),))
    Overrides(tables={"cntct": _entities(phone=("TEL",))}).warn_unused(profile)
    assert caplog.messages == [
        "The overrides give the discriminators of tables otherwise than the profile was counted"
        " with, until scan counts them again: cntct"
    ]
    caplog.clear()
    Overrides().warn_unused(profile)
    assert caplog.messages == [], "a discriminator found, none given"


def test_a_table_agrees_with_the_overrides_where_it_has_the_primary_key_given() -> None:
    (table,) = _PROFILE.tables
    chosen = replace(table, primary_key=PrimaryKey(("frst_nm",)))
    given = replace(table, primary_key=PrimaryKey(("cntct_typ_cd", "frst_nm"), given=True))
    keyed = TableOverride(primary_key=("frst_nm", "cntct_typ_cd"))
    assert keyed.agrees_with(given), "of the same columns, in whatever order"
    assert not keyed.agrees_with(chosen)
    assert not keyed.agrees_with(table), "of none"
    assert TableOverride().agrees_with(chosen), "none given, whatever is chosen"
    assert not TableOverride().agrees_with(given), "given, and no longer"


def test_the_dependencies_of_a_column_given_as_determining_none_are_dropped_laid_over() -> None:
    (table,) = _PROFILE.tables
    dependent = replace(
        table,
        column_dependencies=(
            ColumnDependency(("frst_nm", "cntct_typ_cd"), (), 1.0),
            ColumnDependency(("cntct_typ_cd",), ("frst_nm",), 0.97),
        ),
    )
    given = TableOverride(columns={"cntct_typ_cd": ColumnOverride(determines=False)})
    assert given.determining_none == {"cntct_typ_cd"}
    laid = given.laid_over(dependent)
    assert laid.column_dependencies == (), "of the column as one of the determinants as well"
    assert not given.agrees_with(dependent), "counted anew where a scan resumes"
    assert given.agrees_with(laid)
    kept = TableOverride(columns={"frst_nm": ColumnOverride(determines=False)}).laid_over(dependent)
    assert kept.column_dependencies == dependent.column_dependencies[1:], "of the column alone"


@pytest.mark.parametrize(
    ("given", "problem"),
    [
        (("frst_nm", "kind"), "columns of cntct it does not have: kind"),
        ((), "a primary key of cntct of no columns"),
        (("frst_nm", "frst_nm"), "a primary key of cntct of columns twice: frst_nm"),
    ],
    ids=["a column missing", "no columns", "a column twice"],
)
def test_a_primary_key_given_that_cannot_be_one_is_refused(
    given: tuple[str, ...], problem: str
) -> None:
    with pytest.raises(OverridesError, match=problem):
        TableOverride(primary_key=given).laid_over(_PROFILE.tables[0])


# A profile of contacts whose column `cust_id` may refer to the key of a table of customers.
_RELATED = replace(
    _PROFILE,
    tables=(
        replace(
            _PROFILE.tables[0],
            columns=(*_PROFILE.tables[0].columns, Column("cust_id", "bigint", Statistics(0, 2))),
        ),
        Table("cust", 5, (Column("cust_id", "bigint", Statistics(0, 5)),), keys=(("cust_id",),)),
    ),
)


def _referring(**given: GivenReference) -> Overrides:
    """Overrides that give the references of the columns of `cntct` named, None of nothing given."""
    columns = {name: ColumnOverride(reference=reference) for name, reference in given.items()}
    return Overrides(tables={"cntct": TableOverride(columns=columns)})


def test_the_references_given_are_those_of_the_columns_they_are_given_of() -> None:
    key = ReferenceOverride("cust", "cust_id")
    overrides = _referring(cust_id=key, frst_nm=False, cntct_typ_cd=None)
    assert overrides.references(_RELATED) == {"cntct": {"cust_id": key, "frst_nm": False}}
    assert Overrides().references(_RELATED) == {}, "of no table of none given"


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        (Overrides(tables={"ord": TableOverride()}), "tables that are not profiled: ord"),
        (_referring(kind=False), "columns of cntct it does not have: kind"),
        (
            _referring(cust_id=ReferenceOverride("prod", "prod_id")),
            "cntct.cust_id as a reference to prod, which is not profiled",
        ),
        (
            _referring(cust_id=ReferenceOverride("cust", "cust_no")),
            "cntct.cust_id as a reference to cust.cust_no, which cust does not have",
        ),
        (
            _referring(cust_id=ReferenceOverride("cntct", "cust_id")),
            "cntct.cust_id as a reference to itself",
        ),
    ],
    ids=["a table", "a column", "a table referred to", "a column referred to", "itself"],
)
def test_a_reference_given_that_cannot_be_one_is_refused(
    overrides: Overrides, problem: str
) -> None:
    with pytest.raises(OverridesError, match=re.escape(problem)):
        overrides.references(_RELATED)
    with pytest.raises(OverridesError, match=re.escape(problem)):
        overrides.laid_over(_RELATED)


@pytest.mark.parametrize(
    ("references", "candidates", "given", "warned"),
    [
        ((), (), ReferenceOverride("cust", "cust_id"), True),
        (
            (Reference("cust_id", "cust", "cust_id", 1.0),),
            (),
            ReferenceOverride("cust", "cust_id"),
            True,
        ),
        (
            (Reference("cust_id", "cust", "cust_id", 1.0, given=True),),
            (),
            ReferenceOverride("cust", "cust_id"),
            False,
        ),
        ((), (Reference("cust_id", "cust", "cust_id", 1.0),) * 2, False, True),
        ((), (), False, False),
        ((Reference("cust_id", "cust", "cust_id", 1.0, given=True),), (), None, True),
        ((Reference("cust_id", "cust", "cust_id", 1.0),), (), None, False),
    ],
    ids=[
        "none related",
        "found",
        "as given",
        "candidates of none",
        "none",
        "no longer given",
        "none given",
    ],
)
def test_a_reference_given_otherwise_than_related_is_warned_of(
    caplog: pytest.LogCaptureFixture,
    references: tuple[Reference, ...],
    candidates: tuple[Reference, ...],
    given: GivenReference,
    warned: bool,
) -> None:
    (cntct, cust) = _RELATED.tables
    related = replace(
        _RELATED,
        tables=(replace(cntct, references=references, reference_candidates=candidates), cust),
    )
    _referring(cust_id=given).warn_unused(related)
    expected = (
        "The overrides give the references of columns otherwise than the profile was related"
        " with, until relate relates them again: cntct.cust_id"
    )
    assert caplog.messages == ([expected] if warned else [])


def test_there_are_no_overrides_where_there_are_no_files() -> None:
    assert Overrides.read([]) == Overrides()


def test_the_overrides_of_several_files_are_merged(tmp_path: Path) -> None:
    glossary = tmp_path / "glossary.yml"
    glossary.write_text(
        "format: 7\nglossary:\n  contact: {abbreviations: [cntct]}\n", encoding="utf-8"
    )
    marks = tmp_path / "marks.yml"
    marks.write_text(
        "format: 7\ntables:\n  cntct:\n    columns:\n      frst_nm: {sensitivity: personal}\n",
        encoding="utf-8",
    )
    names = tmp_path / "names.yml"
    names.write_text(
        "format: 7\ntables:\n  cntct: {name: contact, columns: {frst_nm: {name: first_name}}}\n",
        encoding="utf-8",
    )
    overrides = Overrides.read([glossary, marks, names])
    assert overrides.glossary == {"contact": Concept(abbreviations=("cntct",))}
    table = overrides.tables["cntct"]
    assert table.name == "contact"
    assert table.columns["frst_nm"] == ColumnOverride(
        sensitivity=Sensitivity.PERSONAL, name="first_name"
    ), "what two files give of one column"


def test_a_field_given_in_two_files_of_the_overrides_is_refused(tmp_path: Path) -> None:
    first = tmp_path / "first.yml"
    first.write_text("format: 7\ntables:\n  cntct: {name: contact}\n", encoding="utf-8")
    second = tmp_path / "second.yml"
    second.write_text("format: 7\ntables:\n  cntct: {name: contact}\n", encoding="utf-8")
    files = f"{re.escape(str(first))} and in {re.escape(str(second))}"
    with pytest.raises(OverridesError, match=rf"tables\.cntct\.name is given in {files}"):
        Overrides.read([first, second])


def test_the_overrides_of_the_example_project_are_read() -> None:
    overrides = Overrides.read([_EXAMPLE])
    assert overrides.glossary["address"].abbreviations == ("addr", "adr")
    assert overrides.glossary["airplus"].omitted
    assert overrides.glossary["iban"] == Concept(), "without abbreviations and a description"
    marked = overrides.tables["cntct"].columns["frst_nm"]
    assert marked == ColumnOverride(sensitivity=Sensitivity.PERSONAL)
    assert overrides.tables["ord"].sentinels == {"dlvr_pst_cd": ("", "00000")}
    assert overrides.tables["ord_itm"].determining_none == {"prodgrp_nm"}
    assert overrides.tables["cust"].columns["cust_ap_id"].name == "contact_person_id"
    assert overrides.description is not None, "what the database holds"
    assert overrides.tables["ord_itm"].description is not None, "what a table holds"
    discriminator = overrides.tables["prtnr"].discriminator
    assert isinstance(discriminator, DiscriminatorOverride)
    assert discriminator.column == "prtnr_typ_cd"
    assert discriminator.entities["customer"].values == ("K",)
    assert overrides.tables["ord_itm"].primary_key == ("ord_id", "pos_no")
    referring = overrides.tables["ord"].columns["cust_id"].reference
    assert referring == ReferenceOverride("cust", "cust_id")
    assert overrides.tables["prtnr"].columns["cust_no"].reference is False, "none"


def test_the_overrides_of_the_example_project_lay_over_its_profile(
    example_profile: Profile,
) -> None:
    overrides = Overrides.read([_EXAMPLE])
    given = overrides.tables["prtnr"].discriminator
    assert isinstance(given, DiscriminatorOverride)
    # The business partners as a scan with the overrides counts them: as found, with the values
    # given.
    counted = tuple(
        replace(table, discriminator=replace(table.discriminator, given=given.values))
        if table.discriminator is not None
        else table
        for table in example_profile.tables
    )
    laid = overrides.laid_over(replace(example_profile, tables=counted))
    columns = {f"{t.name}.{c.name}": c for t in laid.tables for c in t.columns}
    assert columns["cntct.lst_nm"].sensitivity is Sensitivity.PERSONAL
    assert laid.glossary["address"].abbreviations == ("addr", "adr")
    assert columns["cust.ap_ap_nm"].reading == ("airplus", "contact_person", "name")
    tables = {table.name: table for table in laid.tables}
    assert laid.description == Overrides.read([_EXAMPLE]).description
    assert tables["ord_itm"].description == Overrides.read([_EXAMPLE]).tables["ord_itm"].description
    assert tables["ord"].description is None, "a table of none given"
    discriminator = tables["prtnr"].discriminator
    assert discriminator is not None
    assert [entity.name_given for entity in discriminator.entities] == [
        "customer",
        "supplier",
        "prospect",
        "employee",
    ], "each of the entities that holds the values given of it"


def test_a_concept_is_given_without_abbreviations_and_description(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text("format: 7\nglossary:\n  name: {}\n", encoding="utf-8")
    overrides = Overrides.read([path])
    assert overrides.glossary == {"name": Concept()}
    laid = overrides.laid_over(_PROFILE)
    assert laid.glossary["name"] == Concept(), "though no name has its word"


def test_a_table_is_given_a_separator_of_lists_and_refused_one_that_cannot_be(
    tmp_path: Path,
) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text("format: '7.5'\ntables:\n  cntct: {list_separator: '|'}\n", encoding="utf-8")
    assert Overrides.read([path]).tables["cntct"] == TableOverride(list_separator="|")
    path.write_text("format: '7.5'\ntables:\n  cntct: {list_separator: ab}\n", encoding="utf-8")
    with pytest.raises(OverridesError, match=r"cntct\.list_separator: 'ab' is no separator"):
        Overrides.read([path])


def test_a_table_is_given_no_discriminator_by_false(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text('format: "7.1"\ntables:\n  cntct: {discriminator: false}\n', encoding="utf-8")
    assert Overrides.read([path]).tables["cntct"] == TableOverride(discriminator=False)


def test_overrides_of_another_format_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text("format: 1\nglossary: {}\n", encoding="utf-8")
    version = re.escape(str(FORMAT.version))
    with pytest.raises(
        OverridesError, match=rf"format 1\.0, of another major version than the format {version}"
    ):
        Overrides.read([path])
