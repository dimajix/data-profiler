"""Tests of the profile: written and read as a document, refused where it is not one."""

from pathlib import Path

import pytest
from yaml import safe_dump, safe_load

from data_profiler.detect import SemanticType
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
                    statistics=Statistics(312, 803455, Lengths(2, 74), Range("Aal", "Zwick")),
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
                    matches=(Match(SemanticType.EMAIL, 0.982),),
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
    ],
    ids=["a field missing", "a field unknown", "a field of the wrong type"],
)
def test_a_profile_with_a_wrong_field_is_refused_naming_the_field(
    tmp_path: Path, change: dict[str, object], problem: str
) -> None:
    path = _written(tmp_path, change)
    with pytest.raises(ProfileError, match=problem):
        Profile.read(path)


def test_a_profile_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be read"):
        Profile.read(tmp_path / "profile.yml")


def test_a_profile_that_cannot_be_written_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be written"):
        _PROFILE.write(tmp_path / "missing" / "profile.yml")
