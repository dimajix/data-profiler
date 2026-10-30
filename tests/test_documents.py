"""Tests of documents: written and read as YAML in a format, refused where they are not one."""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from pydantic import TypeAdapter
from yaml import safe_dump, safe_load

from data_profiler.documents import DocumentError, read_document, write_document


@dataclass(frozen=True)
class _Part:
    """A class a document holds within another."""

    name: str


@dataclass(frozen=True)
class _Whole:
    """A class a document holds."""

    name: str
    parts: tuple[_Part, ...]


_ADAPTER: Final = TypeAdapter(_Whole)
_VERSION: Final = 3
_WHOLE: Final = _Whole(name="whole", parts=(_Part("one"), _Part("two")))


def _written(tmp_path: Path, change: dict[str, object] | None = None) -> Path:
    """The document of `_WHOLE`, with the fields of its first part changed as `change` says."""
    path = tmp_path / "document.yml"
    write_document(path, _ADAPTER, _VERSION, _WHOLE)
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
    assert read_document(_written(tmp_path), _ADAPTER, _VERSION) == _WHOLE


def test_a_document_is_written_with_its_format_first(tmp_path: Path) -> None:
    content = safe_load(_written(tmp_path).read_text(encoding="utf-8"))
    assert list(content) == ["format", "name", "parts"]
    assert content["format"] == _VERSION


def test_a_document_written_over_another_replaces_it(tmp_path: Path) -> None:
    path = _written(tmp_path)
    other = _Whole(name="other", parts=())
    write_document(path, _ADAPTER, _VERSION, other)
    assert read_document(path, _ADAPTER, _VERSION) == other
    left = [file.name for file in tmp_path.iterdir()]
    assert left == ["document.yml"], "no temporary file is left"


@pytest.mark.parametrize(
    ("version", "named"),
    [("99", "99"), ("'3'", "'3'"), ("true", "True")],
    ids=["a later format", "a format as text", "a format that is no number"],
)
def test_a_document_of_another_format_is_refused_naming_both(
    tmp_path: Path, version: str, named: str
) -> None:
    path = _written(tmp_path)
    text = path.read_text(encoding="utf-8").replace(f"format: {_VERSION}", f"format: {version}")
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DocumentError, match=f"format {named}, but only format {_VERSION}"):
        read_document(path, _ADAPTER, _VERSION)


def test_a_document_without_a_format_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    path.write_text("name: whole\nparts: []\n", encoding="utf-8")
    with pytest.raises(DocumentError, match="names no format"):
        read_document(path, _ADAPTER, _VERSION)


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
        read_document(path, _ADAPTER, _VERSION)


@pytest.mark.parametrize("text", ["- a list\n", ""], ids=["a list", "nothing"])
def test_a_file_that_holds_no_fields_is_refused(tmp_path: Path, text: str) -> None:
    path = tmp_path / "document.yml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DocumentError, match="holds no fields"):
        read_document(path, _ADAPTER, _VERSION)


def test_a_file_that_is_no_yaml_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    path.write_text("name: [whole\n", encoding="utf-8")
    with pytest.raises(DocumentError, match="is no YAML"):
        read_document(path, _ADAPTER, _VERSION)


def test_a_document_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="cannot be read"):
        read_document(tmp_path / "document.yml", _ADAPTER, _VERSION)


def test_a_document_that_cannot_be_written_leaves_nothing_behind(tmp_path: Path) -> None:
    path = tmp_path / "document.yml"
    path.mkdir()
    with pytest.raises(DocumentError, match="cannot be written"):
        write_document(path, _ADAPTER, _VERSION, _WHOLE)
    left = [file.name for file in tmp_path.iterdir()]
    assert left == ["document.yml"], "no temporary file is left"
    assert path.is_dir(), "what was there before is left as it was"


def test_a_document_in_a_directory_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DocumentError, match="cannot be written"):
        write_document(tmp_path / "missing" / "document.yml", _ADAPTER, _VERSION, _WHOLE)
