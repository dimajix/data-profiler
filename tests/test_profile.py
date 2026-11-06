"""Tests of the profile: written and read as a directory of documents, refused where it is not."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from yaml import safe_dump, safe_load

from data_profiler.detect import EMAIL, SemanticType, Sensitivity
from data_profiler.profile import (
    FORMAT,
    Cardinality,
    Column,
    ColumnDependency,
    ColumnGroup,
    Concept,
    Discriminator,
    Entity,
    Lengths,
    Match,
    PrimaryKey,
    Profile,
    ProfileError,
    Range,
    Reference,
    Run,
    Statistics,
    Table,
    Term,
    Value,
)

_PROFILE = Profile(
    catalog="crm",
    schema="sales",
    tables=(
        Table(
            name="CUST",
            rows=1250000,
            columns=(
                Column(name="CUST_ID", type="bigint", statistics=Statistics(0, 1248113)),
                Column(
                    name="CUST_NM",
                    type="varchar(80)",
                    statistics=Statistics(312, 803455, Lengths(2, 74)),
                    marked=Sensitivity.PERSONAL,
                ),
                Column(
                    name="CUST_TYP_CD",
                    type="varchar(2)",
                    statistics=Statistics(0, 2, Lengths(1, 1), Range("B", "P")),
                    values=(Value("P", 1100000), Value("B", 150000)),
                ),
                Column(
                    name="CUST_EML",
                    type="varchar(120)",
                    statistics=Statistics(0, 1100000, Lengths(9, 96)),
                    matches=(Match(EMAIL, 0.982),),
                ),
            ),
            keys=(("CUST_ID",), ("CUST_NM", "CUST_EML")),
            primary_key=PrimaryKey(("CUST_ID",)),
            column_groups=(ColumnGroup(("CUST_NM", "CUST_EML"), 0.912),),
            column_dependencies=(ColumnDependency(("CUST_EML",), ("CUST_TYP_CD",), 0.97),),
            discriminator=Discriminator(
                "CUST_TYP_CD",
                (
                    Entity(
                        ("P",),
                        1100000,
                        {
                            "CUST_ID": 1100000,
                            "CUST_NM": 1099688,
                            "CUST_TYP_CD": 1100000,
                            "CUST_EML": 1100000,
                        },
                    ),
                    Entity(
                        ("B",),
                        150000,
                        {
                            "CUST_ID": 150000,
                            "CUST_NM": 150000,
                            "CUST_TYP_CD": 150000,
                            "CUST_EML": 0,
                        },
                    ),
                ),
            ),
        ),
    ),
    glossary={
        "customer": Concept(("cust",), "A person or company that buys."),
        "name": Concept(("nm",)),
        "number": Concept(("nm", "no")),
        "airplus": Concept(("ap",), "Marks a custom column.", omitted=True),
        "iban": Concept(),
    },
)

# The start of a run of scan in the past, in UTC, as a profile reads it back.
_STARTED = datetime(2026, 1, 2, 9, 30, 0, 123456, tzinfo=UTC)
# The start of the scan that updates a profile, after it.
_NOW = datetime(2026, 1, 3, 8, 0, tzinfo=UTC)


def _written(tmp_path: Path, change: dict[str, object] | None = None) -> Path:
    """The directory of `_PROFILE`, with the fields of its first column changed as `change` says."""
    _PROFILE.write(tmp_path)
    if change is not None:
        path = tmp_path / "tables" / "CUST.yml"
        content = safe_load(path.read_text(encoding="utf-8"))
        column = content["columns"][0]
        for field, value in change.items():
            if value is None:
                del column[field]
            else:
                column[field] = value
        path.write_text(safe_dump(content), encoding="utf-8")
    return tmp_path


def _content(path: Path) -> Any:
    """What the document `path` holds."""
    return safe_load(path.read_text(encoding="utf-8"))


def test_a_table_of_a_profile_is_found_by_its_name() -> None:
    assert _PROFILE.table("CUST") is _PROFILE.tables[0]
    with pytest.raises(KeyError):
        _PROFILE.table("ORD")


def test_a_column_of_a_table_is_found_by_its_name() -> None:
    (table, *_) = _PROFILE.tables
    assert table.column("CUST_TYP_CD") == table.columns[2]
    with pytest.raises(KeyError):
        table.column("CUST_TYP")


def test_a_profile_written_and_read_is_unchanged(tmp_path: Path) -> None:
    assert Profile.read(_written(tmp_path)) == _PROFILE
    (table,) = _PROFILE.tables
    described = replace(
        _PROFILE, description="A CRM.", tables=(replace(table, description="All."),)
    )
    described.write(tmp_path)
    assert Profile.read(tmp_path) == described, "with what the database and a table hold"


def test_a_profile_is_written_as_its_head_and_a_file_of_each_table(tmp_path: Path) -> None:
    _written(tmp_path)
    head, table = _content(tmp_path / "profile.yml"), _content(tmp_path / "tables" / "CUST.yml")
    assert (head["format"], table["format"]) == (str(FORMAT), str(FORMAT)), "each with its format"
    assert "tables" not in head
    assert (table["name"], table["rows"]) == ("CUST", 1250000)


def test_the_files_of_tables_the_profile_does_not_have_are_removed(tmp_path: Path) -> None:
    replace(_PROFILE, tables=(replace(_PROFILE.tables[0], name="ORD"), *_PROFILE.tables)).write(
        tmp_path
    )
    _PROFILE.write(tmp_path)
    assert [path.name for path in (tmp_path / "tables").iterdir()] == ["CUST.yml"]
    assert Profile.read(tmp_path) == _PROFILE


def test_the_tables_are_read_sorted_by_name(tmp_path: Path) -> None:
    names = ("a", "a.b", "B")
    profile = replace(
        _PROFILE, tables=tuple(replace(_PROFILE.tables[0], name=name) for name in names)
    )
    profile.write(tmp_path)
    assert [table.name for table in Profile.read(tmp_path).tables] == sorted(names)


def test_the_glossary_is_written_as_each_concept_under_its_word(tmp_path: Path) -> None:
    content = _content(_written(tmp_path) / "profile.yml")
    assert content["glossary"] == {
        "customer": {"abbreviations": ["cust"], "description": "A person or company that buys."},
        "name": {"abbreviations": ["nm"]},
        "number": {"abbreviations": ["nm", "no"]},
        "airplus": {
            "abbreviations": ["ap"],
            "description": "Marks a custom column.",
            "omitted": True,
        },
        "iban": {},
    }, "a concept without abbreviations without them"


@pytest.mark.parametrize("name", ["../CUST", "con", ".hidden"])
def test_a_table_whose_name_is_no_name_of_a_file_is_refused(tmp_path: Path, name: str) -> None:
    profile = replace(_PROFILE, tables=(replace(_PROFILE.tables[0], name=name),))
    with pytest.raises(ProfileError, match="no name of a file"):
        profile.write(tmp_path)
    assert not tmp_path.joinpath("profile.yml").exists(), "nothing is written"


@pytest.mark.parametrize(
    ("keys", "primary"),
    [
        ((("CUST_ID",), ("CUST_NO",)), PrimaryKey(("CUST_ID",))),
        ((("CUST_ID",),), PrimaryKey(("CUST_ID", "CUST_NO"))),
    ],
    ids=["a key", "the primary key"],
)
def test_a_key_of_a_column_the_table_does_not_have_is_refused(
    tmp_path: Path, keys: tuple[tuple[str, ...], ...], primary: PrimaryKey
) -> None:
    (table,) = _PROFILE.tables
    keyed = replace(table, keys=keys, primary_key=primary)
    replace(_PROFILE, tables=(keyed,)).write(tmp_path)
    with pytest.raises(ProfileError, match="a key names the column 'CUST_NO', which the table"):
        Profile.read(tmp_path)


@pytest.mark.parametrize(
    ("dependencies", "refused"),
    [
        (
            (ColumnDependency(("CUST_NO",), ("CUST_NM",), 1.0),),
            "a column dependency names the column 'CUST_NO', which the table does not have",
        ),
        (
            (ColumnDependency(("CUST_ID", "CUST_NM"), ("CUST_NM",), 1.0),),
            "the columns of a column dependency name the column 'CUST_NM' twice",
        ),
        (
            (ColumnDependency(("CUST_ID",), (), 1.0),),
            "a column dependency names fewer than two columns",
        ),
        (
            (
                ColumnDependency(("CUST_ID",), ("CUST_NM",), 1.0),
                ColumnDependency(("CUST_ID",), ("CUST_EML",), 1.0),
            ),
            "the determinants of the column dependencies name the column 'CUST_ID' twice",
        ),
    ],
    ids=["of no column", "twice", "of one column", "a determinant twice"],
)
def test_a_column_dependency_that_is_none_of_the_table_is_refused(
    tmp_path: Path, dependencies: tuple[ColumnDependency, ...], refused: str
) -> None:
    (table,) = _PROFILE.tables
    dependent = replace(table, column_dependencies=dependencies)
    replace(_PROFILE, tables=(dependent,)).write(tmp_path)
    with pytest.raises(ProfileError, match=refused):
        Profile.read(tmp_path)


def _with_entities(tmp_path: Path, *entities: Entity, column: str = "CUST_TYP_CD") -> Path:
    """The directory of `_PROFILE`, its table of a discriminator of `column` of `entities`."""
    (table,) = _PROFILE.tables
    discriminated = replace(table, discriminator=Discriminator(column, entities))
    replace(_PROFILE, tables=(discriminated,)).write(tmp_path)
    return tmp_path


def test_a_discriminator_of_a_column_the_table_does_not_have_is_refused(tmp_path: Path) -> None:
    (table,) = _PROFILE.tables
    assert table.discriminator is not None
    entities = table.discriminator.entities
    with pytest.raises(ProfileError, match="the column 'CUST_KIND', which the table does not have"):
        Profile.read(_with_entities(tmp_path, *entities, column="CUST_KIND"))


def test_an_entity_that_does_not_give_the_filled_rows_of_each_column_is_refused(
    tmp_path: Path,
) -> None:
    (table,) = _PROFILE.tables
    assert table.discriminator is not None
    first, second = table.discriminator.entities
    fewer = replace(second, filled={"CUST_ID": 150000})
    with pytest.raises(ProfileError, match="does not give the filled rows of each column"):
        Profile.read(_with_entities(tmp_path, first, fewer))


def test_a_value_of_two_entities_is_refused_without_naming_it(tmp_path: Path) -> None:
    (table,) = _PROFILE.tables
    assert table.discriminator is not None
    first, second = table.discriminator.entities
    twice = replace(second, values=("B", "P"))
    with pytest.raises(ProfileError, match="a value of two entities") as refused:
        Profile.read(_with_entities(tmp_path, first, twice))
    assert "'P'" not in str(refused.value), "a value of the database"


def _of_a_project(account_number: SemanticType) -> Profile:
    """`_PROFILE`, of a project of the type `account_number`, which its first column is of."""
    table = _PROFILE.tables[0]
    column = replace(table.columns[0], matches=(Match(account_number, 1.0, 1.0),))
    table = replace(table, columns=(column, *table.columns[1:]))
    return replace(_PROFILE, tables=(table, *_PROFILE.tables[1:]), types=(account_number,))


def test_a_profile_with_the_types_of_its_project_is_written_and_read_unchanged(
    tmp_path: Path, account_number: SemanticType
) -> None:
    profile = _of_a_project(account_number)
    profile.write(tmp_path)
    assert Profile.read(tmp_path) == profile
    assert _content(tmp_path / "profile.yml")["types"] == {
        "account-number": {"pattern": "A[0-9]{10}", "sensitivity": "personal"}
    }, "as the project gives them"
    table = _content(tmp_path / "tables" / "CUST.yml")
    assert table["columns"][0]["matches"][0]["type"] == "account-number"


def test_a_match_of_a_type_neither_of_the_tool_nor_of_the_project_is_refused(
    tmp_path: Path, account_number: SemanticType
) -> None:
    _of_a_project(account_number).write(tmp_path)
    path = tmp_path / "profile.yml"
    content = _content(path)
    content["types"] = {"customer-number": content["types"]["account-number"]}
    path.write_text(safe_dump(content), encoding="utf-8")
    with pytest.raises(
        ProfileError, match=r"type: Input should be .*'zero-one' or 'customer-number'"
    ):
        Profile.read(tmp_path)


def test_a_profile_with_a_wrong_type_of_its_project_is_refused_naming_it(tmp_path: Path) -> None:
    _PROFILE.write(tmp_path)
    path = tmp_path / "profile.yml"
    content = _content(path)
    content["types"] = {"date": {"pattern": "[0-9]+", "sensitivity": "none"}}
    path.write_text(safe_dump(content), encoding="utf-8")
    with pytest.raises(ProfileError, match="types: date is a semantic type of the tool"):
        Profile.read(tmp_path)


def test_a_profile_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be read"):
        Profile.read(tmp_path)


def test_a_profile_is_written_into_a_directory_it_makes(tmp_path: Path) -> None:
    _PROFILE.write(tmp_path / "environment" / "profile")
    assert Profile.read(tmp_path / "environment" / "profile") == _PROFILE


def test_a_profile_that_cannot_be_written_is_refused(tmp_path: Path) -> None:
    (tmp_path / "profile").write_text("a file, not a directory", encoding="utf-8")
    with pytest.raises(ProfileError, match="cannot be written"):
        _PROFILE.write(tmp_path / "profile")


def test_an_updated_profile_has_the_table_in_place_of_its_own_or_beside_them_sorted() -> None:
    cust = _PROFILE.tables[0]
    counted = replace(cust, rows=1)
    assert _PROFILE.updated(counted).tables == (counted,), "in place of the table of its name"
    added = replace(cust, name="ADDR")
    assert _PROFILE.updated(added).tables == (added, cust), "beside them, sorted by name"


def test_a_table_updated_keeps_what_describe_filled() -> None:
    cust = _PROFILE.tables[0]
    named = replace(cust.columns[0], terms=(Term("cust", ("customer",)), Term("id")))
    read = replace(named, reading=("customer", "id"), description="Who the customer is.")
    described = replace(
        cust,
        columns=(read, *cust.columns[1:]),
        terms=(Term("cust", ("customer",)),),
        reading=("customer",),
    )
    profile = replace(_PROFILE, tables=(described,))
    gone = replace(cust.columns[1], name="CUST_NO")
    (updated,) = profile.updated(replace(cust, rows=1, columns=(cust.columns[0], gone))).tables
    assert (updated.rows, updated.terms, updated.reading) == (1, described.terms, described.reading)
    assert updated.columns[0] == read, "the terms, reading and description of a column of a name"
    assert updated.columns[1] == gone, "none of a column of another name"


def test_what_describe_filled_is_written_and_read_unchanged(tmp_path: Path) -> None:
    cust = _PROFILE.tables[0]
    column = replace(
        cust.columns[0],
        terms=(Term("cust", ("customer",)), Term("id")),
        reading=("customer", "id"),
        description="Who the customer is.",
    )
    profile = replace(_PROFILE, tables=(replace(cust, columns=(column, *cust.columns[1:])),))
    profile.write(tmp_path)
    assert Profile.read(tmp_path) == profile
    written = _content(tmp_path / "tables" / "CUST.yml")["columns"][0]
    assert written["terms"] == [{"text": "cust", "concepts": ["customer"]}, {"text": "id"}]
    assert written["reading"] == ["customer", "id"]
    assert written["description"] == "Who the customer is."


def _related(*references: Reference, reference_candidates: tuple[Reference, ...] = ()) -> Profile:
    """The profile, with a table ORD whose columns refer by `references`, `reference_candidates`."""
    columns = (
        Column(name="ORD_ID", type="bigint", statistics=Statistics(0, 100)),
        Column(name="CUST_ID", type="bigint", statistics=Statistics(0, 40)),
        Column(name="REF_NO", type="bigint", statistics=Statistics(0, 30)),
    )
    ordered = Table(
        name="ORD",
        rows=100,
        columns=columns,
        references=references,
        reference_candidates=reference_candidates,
    )
    return _PROFILE.updated(ordered)


def test_references_and_candidates_are_written_and_read_unchanged(tmp_path: Path) -> None:
    profile = _related(
        Reference("CUST_ID", "CUST", "CUST_ID", 0.97),
        Reference("ORD_ID", "ORD", "ORD_ID", None, given=True),
        reference_candidates=(
            Reference("REF_NO", "CUST", "CUST_ID", 1.0),
            Reference("REF_NO", "ORD", "ORD_ID", 1.0),
        ),
    )
    profile.write(tmp_path)
    assert Profile.read(tmp_path) == profile
    written = _content(tmp_path / "tables" / "ORD.yml")
    assert written["references"][0] == {
        "column": "CUST_ID",
        "table": "CUST",
        "key": "CUST_ID",
        "coverage": 0.97,
    }, "a reference found not marked as given"
    assert [found["table"] for found in written["reference_candidates"]] == ["CUST", "ORD"], (
        "as ranked"
    )


@pytest.mark.parametrize(
    ("references", "candidates", "refused"),
    [
        (
            (Reference("ORD_NO", "CUST", "CUST_ID", 1.0),),
            (),
            "a reference names the column 'ORD_NO', which the table does not have",
        ),
        (
            (Reference("CUST_ID", "CUST", "CUST_ID", 1.0),) * 2,
            (),
            "the references name the column 'CUST_ID' twice",
        ),
        (
            (Reference("REF_NO", "CUST", "CUST_ID", 1.0),),
            (Reference("REF_NO", "ORD", "ORD_ID", 1.0),),
            "the column 'REF_NO' has a reference and reference candidates",
        ),
        (
            (),
            (Reference("REF_NO", "PROD", "PROD_ID", 1.0),),
            "a reference names the table 'PROD', which the profile does not have",
        ),
        (
            (Reference("CUST_ID", "CUST", "CUST_NO", 1.0),),
            (),
            "a reference names the column 'CUST_NO' of the table 'CUST', which it does not have",
        ),
    ],
    ids=["of no column", "twice", "and a candidate", "to no table", "to no column"],
)
def test_a_reference_that_is_none_of_the_profile_is_refused(
    tmp_path: Path,
    references: tuple[Reference, ...],
    candidates: tuple[Reference, ...],
    refused: str,
) -> None:
    _related(*references, reference_candidates=candidates).write(tmp_path)
    with pytest.raises(ProfileError, match=refused):
        Profile.read(tmp_path)


def test_a_table_counted_anew_has_none_of_the_references_of_the_one_it_replaces() -> None:
    profile = _related(Reference("CUST_ID", "CUST", "CUST_ID", 1.0))
    (cust, ordered) = profile.tables
    described = replace(profile, tables=(cust, replace(ordered, terms=(Term("ord"),))))
    (_, anew) = described.updated(replace(ordered, references=())).tables
    assert (anew.terms, anew.references) == ((Term("ord"),), ()), "relate finds them again"


def test_the_references_to_a_column_a_table_counted_anew_no_longer_has_are_dropped() -> None:
    profile = _related(
        Reference("CUST_ID", "CUST", "CUST_ID", 1.0),
        reference_candidates=(
            Reference("REF_NO", "CUST", "CUST_ID", 1.0),
            Reference("REF_NO", "ORD", "ORD_ID", 1.0),
        ),
    )
    (cust, _) = profile.tables
    dropped = replace(cust, columns=cust.columns[1:], keys=(), primary_key=None)
    (_, ordered) = profile.updated(dropped).tables
    assert ordered.references == ()
    assert ordered.reference_candidates == (Reference("REF_NO", "ORD", "ORD_ID", 1.0),), (
        "to others kept"
    )


def test_a_column_that_is_a_key_of_its_table_refers_one_to_one_another_many_to_one() -> None:
    (table,) = _PROFILE.tables
    assert table.cardinality(Reference("CUST_ID", "ORD", "CUST_ID", 1.0)) is Cardinality.ONE
    assert table.cardinality(Reference("CUST_EML", "ORD", "EML", 1.0)) is Cardinality.MANY, (
        "of a key of two columns alone"
    )


def test_the_references_to_a_table_are_those_of_the_tables_that_refer() -> None:
    profile = _related(
        Reference("CUST_ID", "CUST", "CUST_ID", 1.0),
        Reference("ORD_ID", "ORD", "ORD_ID", 1.0),
        reference_candidates=(Reference("REF_NO", "CUST", "CUST_ID", 1.0),),
    )
    ordered = profile.table("ORD")
    assert profile.referring("CUST") == [(ordered, ordered.references[0])], "no candidate"
    assert profile.referring("ORD") == [(ordered, ordered.references[1])], "of itself as well"


def test_a_restricted_profile_drops_the_references_to_the_tables_it_drops() -> None:
    profile = _related(
        Reference("CUST_ID", "CUST", "CUST_ID", 1.0),
        Reference("ORD_ID", "ORD", "ORD_ID", 1.0),
        reference_candidates=(
            Reference("REF_NO", "CUST", "CUST_ID", 1.0),
            Reference("REF_NO", "ORD", "ORD_ID", 1.0),
        ),
    )
    (ordered,) = profile.restricted({"ORD"}).tables
    assert ordered.references == (Reference("ORD_ID", "ORD", "ORD_ID", 1.0),)
    assert ordered.reference_candidates == (Reference("REF_NO", "ORD", "ORD_ID", 1.0),)


def test_a_restricted_profile_has_the_tables_named_alone() -> None:
    profile = _PROFILE.updated(replace(_PROFILE.tables[0], name="ORD"))
    assert [table.name for table in profile.restricted({"ORD", "PROD"}).tables] == ["ORD"]
    assert profile.restricted(["CUST", "ORD"]) == profile


def test_a_scan_updates_an_empty_profile_of_a_new_run_where_there_is_none(tmp_path: Path) -> None:
    (tmp_path / "tables").mkdir()
    for directory in (tmp_path / "missing", tmp_path):
        updating = Profile.updating(directory, "crm", "sales", (), _NOW)
        assert updating.tables == (), f"{directory} holds no profile"
        assert updating.run == Run(started=_NOW), "a new run is begun"


def test_a_scan_updates_the_profile_there_is_in_a_new_run(tmp_path: Path) -> None:
    _PROFILE.write(tmp_path)
    updating = Profile.updating(tmp_path, "crm", "sales", (), _NOW)
    assert replace(updating, run=None) == _PROFILE
    assert updating.run is not None, "the profile of no run is scanned in a new one"


def test_a_run_that_did_not_finish_is_resumed_and_one_that_did_followed_by_a_new_one(
    tmp_path: Path,
) -> None:
    resumed = replace(_PROFILE, run=Run(started=_STARTED))
    resumed.write(tmp_path)
    assert Profile.updating(tmp_path, "crm", "sales", (), _NOW) == resumed
    resumed.finished(_NOW).write(tmp_path)
    later = datetime(2026, 1, 4, tzinfo=UTC)
    assert Profile.updating(tmp_path, "crm", "sales", (), later).run == Run(started=later)


def test_a_scan_with_other_types_keeps_the_tables_without_their_matches_and_values(
    tmp_path: Path, account_number: SemanticType
) -> None:
    cust = _PROFILE.tables[0]
    read = replace(cust, reading=("customer",))
    replace(_PROFILE, tables=(read,), run=Run(_STARTED)).write(tmp_path)
    updating = Profile.updating(tmp_path, "crm", "sales", (account_number,), _NOW)
    assert (updating.types, updating.run) == ((account_number,), Run(_NOW)), "in a new run"
    assert updating.glossary == _PROFILE.glossary, "the glossary is kept"
    (table,) = updating.tables
    assert table.reading == ("customer",), "what describe filled is kept"
    assert [c.matches for c in table.columns] == [()] * len(cust.columns)
    assert [c.values for c in table.columns] == [()] * len(cust.columns)
    assert [c.statistics.range for c in table.columns] == [None] * len(cust.columns)
    assert table.discriminator is None, "whose values are values of its column"
    assert [c.statistics.nulls for c in table.columns] == [c.statistics.nulls for c in cust.columns]


def test_a_profile_of_its_schema_is_read_and_one_of_another_refused(tmp_path: Path) -> None:
    _PROFILE.write(tmp_path)
    assert Profile.read_of(tmp_path, "crm", "sales") == _PROFILE
    with pytest.raises(ProfileError, match=r"is of crm\.sales, not of crm\.billing"):
        Profile.read_of(tmp_path, "crm", "billing")


def test_a_scan_of_another_schema_refuses_the_profile(tmp_path: Path) -> None:
    _PROFILE.write(tmp_path)
    with pytest.raises(ProfileError, match=r"is of crm\.sales, not of crm\.billing"):
        Profile.updating(tmp_path, "crm", "billing", (), _NOW)


def test_a_profile_with_its_run_and_the_runs_of_its_tables_is_written_and_read_unchanged(
    tmp_path: Path,
) -> None:
    run = Run(started=_STARTED, finished=datetime(2026, 1, 2, 11, 0, tzinfo=UTC))
    profile = replace(_PROFILE, run=run).updated(replace(_PROFILE.tables[0], rows=1))
    profile.write(tmp_path)
    assert Profile.read(tmp_path) == profile
    table = _content(tmp_path / "tables" / "CUST.yml")
    assert list(table)[:3] == ["format", "name", "run"], "the run of a table follows its name"


def test_a_table_updated_is_counted_by_the_run_of_the_profile() -> None:
    profile = replace(_PROFILE, run=Run(started=_STARTED))
    assert profile.counted("CUST") is None, "a table of another run"
    updated = profile.updated(_PROFILE.tables[0])
    assert updated.tables[0].run == _STARTED
    assert updated.counted("CUST") == updated.tables[0]
    assert updated.counted("ORD") is None, "a table the profile does not have"
    assert _PROFILE.updated(_PROFILE.tables[0]).counted("CUST") is None, "a profile of no run"


def test_a_finished_run_keeps_its_start() -> None:
    finished = replace(_PROFILE, run=Run(started=_STARTED)).finished(_NOW)
    assert finished.run == Run(started=_STARTED, finished=_NOW)
    assert _PROFILE.finished(_NOW) == _PROFILE, "a profile of no run is left as it is"


def test_a_run_that_did_not_finish_of_other_types_is_followed_by_a_new_one(
    tmp_path: Path, account_number: SemanticType
) -> None:
    replace(_PROFILE, run=Run(started=_STARTED)).write(tmp_path)
    updating = Profile.updating(tmp_path, "crm", "sales", (account_number,), _NOW)
    assert updating.run == Run(started=_NOW), "a new run, as the tables are counted anew"
