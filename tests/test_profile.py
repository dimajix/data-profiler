"""Tests of the profile: written and read as YAML, refused where it is not one."""

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


def test_a_profile_written_over_another_replaces_it(tmp_path: Path) -> None:
    path = _written(tmp_path)
    other = Profile(catalog="crm", schema="billing", tables=())
    other.write(path)
    assert Profile.read(path) == other
    left = [file.name for file in tmp_path.iterdir()]
    assert left == ["profile.yml"], "no temporary file is left"


@pytest.mark.parametrize(
    ("version", "named"),
    [("99", "99"), ("'1'", "'1'"), ("true", "True")],
    ids=["a later format", "a format as text", "a format that is no number"],
)
def test_a_profile_of_another_format_is_refused_naming_both(
    tmp_path: Path, version: str, named: str
) -> None:
    path = _written(tmp_path)
    text = path.read_text(encoding="utf-8").replace(f"format: {FORMAT}", f"format: {version}")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ProfileError, match=f"format {named}, but only format {FORMAT}"):
        Profile.read(path)


def test_a_profile_without_a_format_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "profile.yml"
    path.write_text("catalog: crm\nschema: sales\ntables: []\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="names no format"):
        Profile.read(path)


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


def test_a_file_that_is_no_profile_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "profile.yml"
    path.write_text("- a list\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="holds no profile"):
        Profile.read(path)


def test_a_profile_that_cannot_be_written_leaves_nothing_behind(tmp_path: Path) -> None:
    path = tmp_path / "profile.yml"
    path.mkdir()
    with pytest.raises(ProfileError, match="cannot be written"):
        _PROFILE.write(path)
    left = [file.name for file in tmp_path.iterdir()]
    assert left == ["profile.yml"], "no temporary file is left"
    assert path.is_dir(), "what was there before is left as it was"


def test_a_profile_in_a_directory_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be written"):
        _PROFILE.write(tmp_path / "missing" / "profile.yml")


def test_a_profile_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot be read"):
        Profile.read(tmp_path / "profile.yml")


def test_a_file_that_is_no_yaml_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "profile.yml"
    path.write_text("catalog: [crm\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="is no YAML"):
        Profile.read(path)
