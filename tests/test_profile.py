"""Tests of the profile: written and read as a document, refused where it is not one."""

from dataclasses import replace
from pathlib import Path

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
    """The file of `_PROFILE`, with the fields of its first column changed as `change` says."""
    path = tmp_path / "profile.yml"
    _PROFILE.write(path)
    if change is not None:
        content = safe_load(path.read_text(encoding="utf-8"))
        column = content["tables"][0]["columns"][0]
        for field, value in change.items():
            if value is None:
                del column[field]
            else:
                column[field] = value
        path.write_text(safe_dump(content), encoding="utf-8")
    return path


def test_a_profile_written_and_read_is_unchanged(tmp_path: Path) -> None:
    assert Profile.read(_written(tmp_path)) == _PROFILE


def test_a_profile_is_written_with_its_format(tmp_path: Path) -> None:
    content = safe_load(_written(tmp_path).read_text(encoding="utf-8"))
    assert content["format"] == FORMAT


def test_the_glossary_is_written_as_each_term_with_its_word(tmp_path: Path) -> None:
    content = safe_load(_written(tmp_path).read_text(encoding="utf-8"))
    assert content["glossary"] == {"cust": "customer", "nm": "name"}


def test_a_match_is_written_by_the_name_of_its_type(tmp_path: Path) -> None:
    content = safe_load(_written(tmp_path).read_text(encoding="utf-8"))
    assert content["tables"][0]["columns"][3]["matches"] == [{"type": "email", "sample": 0.982}]
    assert "matches" not in content["tables"][0]["columns"][0], (
        "a column without matches has no field matches"
    )


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"statistics": None}, r"tables\.0\.columns\.0\.statistics: .*required"),
        ({"colour": "blue"}, r"tables\.0\.columns\.0\.colour: Unexpected"),
        ({"name": ["CUST", "ID"]}, r"tables\.0\.columns\.0\.name: .*string"),
        (
            {"matches": [{"type": "account", "sample": 1.0}]},
            r"tables\.0\.columns\.0\.matches\.0\.type: Input should be 'email', .* or 'uuid'",
        ),
    ],
    ids=["a field missing", "a field unknown", "a field of the wrong type", "a type unknown"],
)
def test_a_profile_with_a_wrong_field_is_refused_naming_the_field(
    tmp_path: Path, change: dict[str, object], problem: str
) -> None:
    path = _written(tmp_path, change)
    with pytest.raises(ProfileError, match=problem):
        Profile.read(path)


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
    path = tmp_path / "profile.yml"
    profile.write(path)
    assert Profile.read(path) == profile
    content = safe_load(path.read_text(encoding="utf-8"))
    assert content["types"] == {
        "account-number": {"pattern": "A[0-9]{10}", "sensitivity": "personal"}
    }, "as the project gives them"
    assert content["tables"][0]["columns"][0]["matches"][0]["type"] == "account-number"


def test_a_match_of_a_type_neither_of_the_tool_nor_of_the_project_is_refused(
    tmp_path: Path, account_number: SemanticType
) -> None:
    path = tmp_path / "profile.yml"
    _of_a_project(account_number).write(path)
    content = safe_load(path.read_text(encoding="utf-8"))
    content["types"] = {"customer-number": content["types"]["account-number"]}
    path.write_text(safe_dump(content), encoding="utf-8")
    with pytest.raises(ProfileError, match=r"type: Input should be .*'uuid' or 'customer-number'"):
        Profile.read(path)


def test_a_profile_with_a_wrong_type_of_its_project_is_refused_naming_it(tmp_path: Path) -> None:
    path = tmp_path / "profile.yml"
    _PROFILE.write(path)
    content = safe_load(path.read_text(encoding="utf-8"))
    content["types"] = {"date": {"pattern": "[0-9]+", "sensitivity": "none"}}
    path.write_text(safe_dump(content), encoding="utf-8")
    with pytest.raises(ProfileError, match="types: date is a semantic type of the tool"):
        Profile.read(path)


def test_a_profile_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be read"):
        Profile.read(tmp_path / "profile.yml")


def test_a_profile_that_cannot_be_written_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be written"):
        _PROFILE.write(tmp_path / "missing" / "profile.yml")
