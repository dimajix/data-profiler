"""Tests of the profile: written and read as a directory of documents, refused where it is not."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from yaml import safe_dump, safe_load

from data_profiler.detect import EMAIL, SemanticType, Sensitivity
from data_profiler.profile import (
    FORMAT,
    Column,
    Lengths,
    Match,
    Profile,
    ProfileError,
    Range,
    Statistics,
    Table,
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
        ),
    ),
    glossary={"cust": "customer", "nm": "name"},
)


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


def test_a_profile_written_and_read_is_unchanged(tmp_path: Path) -> None:
    assert Profile.read(_written(tmp_path)) == _PROFILE


def test_a_profile_is_written_as_its_head_and_a_file_of_each_table(tmp_path: Path) -> None:
    _written(tmp_path)
    head, table = _content(tmp_path / "profile.yml"), _content(tmp_path / "tables" / "CUST.yml")
    assert (head["format"], table["format"]) == (FORMAT, FORMAT), "each with its format"
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


def test_the_glossary_is_written_as_each_term_with_its_word(tmp_path: Path) -> None:
    content = _content(_written(tmp_path) / "profile.yml")
    assert content["glossary"] == {"cust": "customer", "nm": "name"}


def test_a_match_is_written_by_the_name_of_its_type(tmp_path: Path) -> None:
    content = _content(_written(tmp_path) / "tables" / "CUST.yml")
    assert content["columns"][3]["matches"] == [{"type": "email", "sample": 0.982}]
    assert "matches" not in content["columns"][0], "a column without matches has no field matches"


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"statistics": None}, r"CUST\.yml: columns\.0\.statistics: .*required"),
        ({"colour": "blue"}, r"CUST\.yml: columns\.0\.colour: Unexpected"),
        ({"name": ["CUST", "ID"]}, r"CUST\.yml: columns\.0\.name: .*string"),
        (
            {"matches": [{"type": "account", "sample": 1.0}]},
            r"CUST\.yml: columns\.0\.matches\.0\.type: Input should be 'email', .* or 'uuid'",
        ),
    ],
    ids=["a field missing", "a field unknown", "a field of the wrong type", "a type unknown"],
)
def test_a_profile_with_a_wrong_field_is_refused_naming_the_field(
    tmp_path: Path, change: dict[str, object], problem: str
) -> None:
    directory = _written(tmp_path, change)
    with pytest.raises(ProfileError, match=problem):
        Profile.read(directory)


def test_a_file_of_a_table_of_another_name_is_refused(tmp_path: Path) -> None:
    _written(tmp_path)
    (tmp_path / "tables" / "CUST.yml").rename(tmp_path / "tables" / "ORD.yml")
    with pytest.raises(ProfileError, match=r"ORD\.yml holds the table 'CUST'"):
        Profile.read(tmp_path)


@pytest.mark.parametrize("name", ["../CUST", "con", ".hidden"])
def test_a_table_whose_name_is_no_name_of_a_file_is_refused(tmp_path: Path, name: str) -> None:
    profile = replace(_PROFILE, tables=(replace(_PROFILE.tables[0], name=name),))
    with pytest.raises(ProfileError, match="no name of a file"):
        profile.write(tmp_path)
    assert not tmp_path.joinpath("profile.yml").exists(), "nothing is written"


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
    with pytest.raises(ProfileError, match=r"type: Input should be .*'uuid' or 'customer-number'"):
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
