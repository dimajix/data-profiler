"""Tests of the profile: written and read as a document, refused where it is not one."""

from pathlib import Path

import pytest
from yaml import safe_dump, safe_load

from data_profiler.profile import FORMAT, Column, Lengths, Profile, ProfileError, Statistics, Table

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
                ),
            ),
        ),
    ),
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
