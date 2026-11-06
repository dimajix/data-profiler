"""Tests of documents: written and read as YAML in a version of a format, also several merged."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

import pytest
from yaml import safe_dump, safe_load

from data_profiler.documents import DocumentError, Format, Version


@dataclass(frozen=True)
class _Part:
    """A class a document holds within another."""

    name: str


@dataclass(frozen=True)
class _Whole:
    """A class a document holds."""

    name: str
    parts: tuple[_Part, ...] = ()


@dataclass(frozen=True)
class _Entry:
    """An entry of a map a document holds, of fields that may each be given or not."""

    colour: str | None = None
    size: int | None = None


@dataclass(frozen=True)
class _Entries:
    """A class a document holds that several documents may give parts of."""

    entries: Mapping[str, _Entry | Literal[False]] = field(default_factory=dict)
    tags: tuple[str, ...] = ()


_FORMAT: Final = Format(_Whole, Version(3, 2))
_MERGED: Final = Format(_Entries, Version(3, 2))
_WHOLE: Final = _Whole(name="whole", parts=(_Part("one"), _Part("two")))


def _written(tmp_path: Path, change: dict[str, object] | None = None) -> Path:
    """The document of `_WHOLE`, with the fields of its first part changed as `change` says."""
    path = tmp_path / "document.yml"
    _FORMAT.write(path, _WHOLE)
    if change is not None:
        content = safe_load(path.read_text(encoding="utf-8"))
        part = content["parts"][0]
        for field, value in change.items():
            if value is None:
                del part[field]
            else:
                part[field] = value
        path.write_text(safe_dump(content), encoding="utf-8")
    return path


def test_a_document_written_and_read_is_unchanged(tmp_path: Path) -> None:
    assert _FORMAT.read(_written(tmp_path)) == _WHOLE


def test_a_document_is_written_with_its_format_first(tmp_path: Path) -> None:
    content = safe_load(_written(tmp_path).read_text(encoding="utf-8"))
    assert list(content) == ["format", "name", "parts"]
    assert content["format"] == "3.2", "the version is written as a string, its two parts apart"


def test_a_field_that_has_its_default_is_not_written(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    _FORMAT.write(path, _Whole(name="whole"))
    assert safe_load(path.read_text(encoding="utf-8")) == {"format": "3.2", "name": "whole"}
    assert _FORMAT.read(path) == _Whole(name="whole")


def test_a_document_written_over_another_replaces_it(tmp_path: Path) -> None:
    path = _written(tmp_path)
    other = _Whole(name="other", parts=())
    _FORMAT.write(path, other)
    assert _FORMAT.read(path) == other
    left = [file.name for file in tmp_path.iterdir()]
    assert left == ["document.yml"], "no temporary file is left"


def _of_format(tmp_path: Path, version: str) -> Path:
    """The document of `_WHOLE`, its field `format` written as `version`."""
    path = _written(tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "format: '3.2'" in text, "the version is written as the field is replaced"
    path.write_text(text.replace("format: '3.2'", f"format: {version}"), encoding="utf-8")
    return path


def test_a_document_of_an_older_minor_version_is_read_with_the_defaults_of_what_it_lacks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "document.yml"
    path.write_text("format: '3.0'\nname: whole\n", encoding="utf-8")
    assert _FORMAT.read(path) == _Whole(name="whole")


def test_a_format_given_as_a_number_is_of_minor_version_0(tmp_path: Path) -> None:
    assert _FORMAT.read(_of_format(tmp_path, "3")) == _WHOLE


def test_a_document_of_a_newer_minor_version_is_refused_as_newer_than_the_tool(
    tmp_path: Path,
) -> None:
    path = _of_format(tmp_path, "'3.3'")
    with pytest.raises(
        DocumentError,
        match=r"format 3\.3, newer than the format 3\.2 that is read: the tool is older",
    ):
        _FORMAT.read(path)


@pytest.mark.parametrize(
    ("version", "named"),
    [("'4.0'", "4.0"), ("'2.2'", "2.2"), ("4", "4.0")],
    ids=["a later major version", "an earlier major version", "a major version as a number"],
)
def test_a_document_of_another_major_version_is_refused_naming_both(
    tmp_path: Path, version: str, named: str
) -> None:
    path = _of_format(tmp_path, version)
    with pytest.raises(
        DocumentError,
        match=rf"format {re.escape(named)}, of another major version than the format 3\.2",
    ):
        _FORMAT.read(path)


@pytest.mark.parametrize(
    ("version", "named"),
    [("3.2", "3.2"), ("'3'", "'3'"), ("'3.2.1'", "'3.2.1'"), ("true", "True")],
    ids=["a number of a fraction", "a major version alone as text", "three parts", "no number"],
)
def test_a_document_of_a_format_that_is_no_version_is_refused(
    tmp_path: Path, version: str, named: str
) -> None:
    path = _of_format(tmp_path, version)
    with pytest.raises(
        DocumentError, match=f"names the format {re.escape(named)}, which is no version"
    ):
        _FORMAT.read(path)


def test_a_document_without_a_format_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    path.write_text("name: whole\nparts: []\n", encoding="utf-8")
    with pytest.raises(DocumentError, match="names no format"):
        _FORMAT.read(path)


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"name": None}, r"parts\.0\.name: .*required"),
        ({"colour": "blue"}, r"parts\.0\.colour: Unexpected"),
        ({"name": ["one", "two"]}, r"parts\.0\.name: .*string"),
    ],
    ids=["a field missing", "a field unknown", "a field of the wrong type"],
)
def test_a_document_with_a_wrong_field_is_refused_naming_the_field(
    tmp_path: Path, change: dict[str, object], problem: str
) -> None:
    path = _written(tmp_path, change)
    with pytest.raises(DocumentError, match=problem):
        _FORMAT.read(path)


@pytest.mark.parametrize("text", ["- a list\n", ""], ids=["a list", "nothing"])
def test_a_file_that_holds_no_fields_is_refused(tmp_path: Path, text: str) -> None:
    path = tmp_path / "document.yml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DocumentError, match="holds no fields"):
        _FORMAT.read(path)


def test_a_file_that_is_no_yaml_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    path.write_text("name: [whole\n", encoding="utf-8")
    with pytest.raises(DocumentError, match="is no YAML"):
        _FORMAT.read(path)


def test_a_document_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="cannot be read"):
        _FORMAT.read(tmp_path / "document.yml")


def test_a_document_that_cannot_be_written_leaves_nothing_behind(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    path.mkdir()
    with pytest.raises(DocumentError, match="cannot be written"):
        _FORMAT.write(path, _WHOLE)
    left = [file.name for file in tmp_path.iterdir()]
    assert left == ["document.yml"], "no temporary file is left"
    assert path.is_dir(), "what was there before is left as it was"


def test_a_document_in_a_directory_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="cannot be written"):
        _FORMAT.write(tmp_path / "missing" / "document.yml", _WHOLE)


def _document(tmp_path: Path, name: str, text: str) -> Path:
    """The document `name` in `tmp_path`, of the format 3.2 unless `text` begins with another."""
    path = tmp_path / name
    path.write_text(text if text.startswith("format:") else f"format: '3.2'\n{text}", "utf-8")
    return path


def test_documents_read_merged_are_merged_key_by_key(tmp_path: Path) -> None:
    first = _document(tmp_path, "first.yml", "entries:\n  one: {colour: red}\n")
    second = _document(
        tmp_path, "second.yml", "entries:\n  one: {size: 2}\n  two: false\ntags: [a]\n"
    )
    assert _MERGED.read_merged([first, second]) == _Entries(
        entries={"one": _Entry(colour="red", size=2), "two": False}, tags=("a",)
    )


def test_no_documents_read_merged_are_the_empty_document() -> None:
    assert _MERGED.read_merged([]) == _Entries()


@pytest.mark.parametrize(
    ("first", "second", "field"),
    [
        ("entries: {one: {colour: red}}", "entries: {one: {colour: blue}}", "entries.one.colour"),
        ("entries: {one: {colour: red}}", "entries: {one: {colour: red}}", "entries.one.colour"),
        ("tags: [a]", "tags: [b]", "tags"),
        ("entries: {one: {colour: red}}", "entries: {one: false}", "entries.one"),
    ],
    ids=["of other values", "of the same value", "a list", "a map and a value"],
)
def test_a_field_given_in_two_documents_is_refused_naming_it_and_both_files(
    tmp_path: Path, first: str, second: str, field: str
) -> None:
    paths = [_document(tmp_path, "first.yml", first), _document(tmp_path, "second.yml", second)]
    files = " and in ".join(re.escape(str(path)) for path in paths)
    with pytest.raises(DocumentError, match=f"^{re.escape(field)} is given in {files}$"):
        _MERGED.read_merged(paths)


def test_a_field_given_in_two_documents_names_the_one_whose_map_it_is_in(tmp_path: Path) -> None:
    first = _document(tmp_path, "first.yml", "entries: {one: {colour: red}}")
    second = _document(tmp_path, "second.yml", "entries: {two: {size: 2}}")
    third = _document(tmp_path, "third.yml", "entries: {one: {colour: red}}")
    with pytest.raises(
        DocumentError, match=f"is given in {re.escape(str(first))} and in {re.escape(str(third))}"
    ):
        _MERGED.read_merged([first, second, third])


def test_a_map_of_an_anchor_extended_by_another_document_is_extended_where_it_is_given(
    tmp_path: Path,
) -> None:
    first = _document(tmp_path, "first.yml", "entries: {one: &red {colour: red}, two: *red}")
    second = _document(tmp_path, "second.yml", "entries: {one: {size: 2}}")
    assert _MERGED.read_merged([first, second]).entries == {
        "one": _Entry(colour="red", size=2),
        "two": _Entry(colour="red"),
    }, "not at the other alias of the anchor"


def test_each_document_read_merged_is_read_by_its_own_version(tmp_path: Path) -> None:
    older = _document(tmp_path, "older.yml", "format: '3.0'\ntags: [a]\n")
    newer = _document(tmp_path, "newer.yml", "format: '3.3'\nentries: {}\n")
    assert _MERGED.read_merged([older]) == _Entries(tags=("a",))
    with pytest.raises(DocumentError, match=rf"^{re.escape(str(newer))} is of format 3\.3, newer"):
        _MERGED.read_merged([older, newer])


def test_a_field_of_the_wrong_type_in_a_document_read_merged_is_refused_naming_its_file(
    tmp_path: Path,
) -> None:
    right = _document(tmp_path, "right.yml", "tags: [a]")
    wrong = _document(tmp_path, "wrong.yml", "entries: {one: {size: big}}")
    with pytest.raises(DocumentError, match=rf"^{re.escape(str(wrong))}: entries\.one\..*size"):
        _MERGED.read_merged([right, wrong])
