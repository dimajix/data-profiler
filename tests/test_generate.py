"""Tests of the generated parts of the documents: references of formats and files, written anew."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Final, Literal

import pytest
from pydantic import AfterValidator, BeforeValidator, PlainValidator

from data_profiler.detect import Sensitivity
from data_profiler.documents import Format, Version
from generate import GenerateError, check, generated, main, reference, write


@dataclass(frozen=True)
class _Part:
    """A class within the class of a document.

    Attributes:
        name: Its name.
    """

    name: str


@dataclass(frozen=True)
class _Whole:
    """The class of a document.

    What it holds, in detail.

    Attributes:
        name: Its name, which a
            description of two lines gives.
        parts: Its parts, by their names.
        sensitivity: Its sensitivity, or None.
        given: A part, or False for none.
        counted: Whether it was counted.
    """

    name: str
    parts: dict[str, _Part] = field(default_factory=dict)
    sensitivity: Sensitivity | None = None
    given: _Part | Literal[False] | None = None
    counted: bool = False


_FORMAT: Final = Format(_Whole, Version(2, 1))


@dataclass(frozen=True)
class _Measured:
    """A class of a field required that may be None.

    Attributes:
        share: Its share, or None where it is not measured.
    """

    share: float | None


@dataclass(frozen=True)
class _Checked:
    """A class of fields of validators of their own.

    Attributes:
        code: Its code, checked once it is read.
        size: Its size, read by a validator.
    """

    code: Annotated[str, AfterValidator(str.upper)]
    size: Annotated[int, PlainValidator(int, json_schema_input_type=str)]


@dataclass(frozen=True)
class _Unread:
    """A class of a field read by a validator that names not what it reads.

    Attributes:
        size: Its size.
    """

    size: Annotated[int, PlainValidator(int)]


@dataclass(frozen=True)
class _ReadBefore:
    """A class of a field read first by a validator that names not what it reads.

    Attributes:
        size: Its size.
    """

    size: Annotated[int, BeforeValidator(int)]


@dataclass(frozen=True)
class _Undescribed:
    """A class whose field has no description.

    Attributes:
        name: Its name.
    """

    name: str
    size: int


@dataclass(frozen=True)
class _Unknown:
    """A class whose field is of a type the reference does not know.

    Attributes:
        size: Its size.
    """

    size: complex


def test_a_reference_begins_with_the_document_and_its_version() -> None:
    text = reference("whole.yml", _FORMAT)
    assert text.startswith('### `whole.yml`\n\nThe document begins with `format: "2.1"`')
    assert "The class of a document.\n\nWhat it holds, in detail." in text, "its whole description"


def test_a_reference_holds_each_field_with_its_type_default_and_description() -> None:
    text = reference("whole.yml", _FORMAT)
    assert (
        "| `name` | text | required | Its name, which a description of two lines gives. |" in text
    )
    assert "| `parts` | map of [Part](#part) | empty | Its parts, by their names. |" in text
    assert "| `sensitivity` | `none`, `personal` or `payment-card` | absent |" in text
    assert "| `given` | [Part](#part) or `false` | absent |" in text
    assert "| `counted` | boolean | `false` |" in text


def test_a_field_required_that_may_be_none_is_written_null() -> None:
    text = reference("measured.yml", Format(_Measured, Version(1, 0)))
    assert "| `share` | number or `null` | required |" in text


def test_a_field_of_a_validator_is_written_as_the_type_it_is_read_as() -> None:
    text = reference("checked.yml", Format(_Checked, Version(1, 0)))
    assert "| `code` | text | required |" in text, "checked once it is read as text"
    assert "| `size` | text | required |" in text, "read from text by its validator"


def test_a_reference_holds_each_class_within_once_under_its_name() -> None:
    text = reference("whole.yml", _FORMAT)
    assert text.count("#### Part\n\nA class within the class of a document.") == 1


@pytest.mark.parametrize(
    ("root", "problem"),
    [
        (_Undescribed, r"_Undescribed\.size: it has no description"),
        (_Unknown, r"_Unknown\.size: its type .* not known"),
        (_Unread, r"_Unread\.size: its type .* names no json_schema_input_type"),
        (_ReadBefore, r"_ReadBefore\.size: its type .* names no json_schema_input_type"),
    ],
    ids=[
        "a field without a description",
        "a type not known",
        "a validator reading anything",
        "a validator reading anything first",
    ],
)
def test_a_reference_of_what_it_cannot_write_fails(root: type, problem: str) -> None:
    with pytest.raises(GenerateError, match=problem):
        reference("whole.yml", Format(root, Version(1, 0)))


def test_a_generated_part_is_written_anew_and_the_rest_kept() -> None:
    text = (
        "# Hand\n\n<!-- begin reference: overrides.yml -->\nold\n"
        "<!-- end reference: overrides.yml -->\n\nWritten by hand.\n"
    )
    written = generated(text)
    assert written.startswith(
        "# Hand\n\n<!-- begin reference: overrides.yml -->\n### `overrides.yml`"
    )
    assert "\nold\n" not in written, "what stood between the markers is replaced"
    assert written.endswith("<!-- end reference: overrides.yml -->\n\nWritten by hand.\n")
    assert generated(written) == written, "what is written is written again the same"


def test_a_file_is_written_as_a_code_block_of_yaml() -> None:
    text = (
        "<!-- begin file: examples/crm/project.yml -->\n<!-- end file: examples/crm/project.yml -->"
    )
    assert generated(text).startswith(
        "<!-- begin file: examples/crm/project.yml -->\n```yaml\n# The example project"
    )


@pytest.mark.parametrize(
    ("marker", "problem"),
    [("reference: other.yml", "no format of other.yml"), ("file: missing.yml", "cannot be read")],
    ids=["a format not known", "a file missing"],
)
def test_a_marker_of_what_is_not_there_fails(marker: str, problem: str) -> None:
    with pytest.raises(GenerateError, match=problem):
        generated(f"<!-- begin {marker} -->\n<!-- end {marker} -->\n")


@pytest.mark.parametrize(
    "text",
    [
        "<!-- begin file: examples/crm/project.yml -->\n",
        "<!-- begin file: examples/crm/project.yml -->\n"
        "<!-- end file: examples/crm/other.yml -->\n",
    ],
    ids=["no end", "an end of another name"],
)
def test_a_marker_without_its_partner_fails(text: str) -> None:
    with pytest.raises(GenerateError, match="has no partner"):
        generated(text)


_STALE: Final = (
    "# Written by hand\n\n<!-- begin reference: project.yml -->\n"
    "<!-- end reference: project.yml -->\n"
)


def test_documents_whose_generated_parts_are_stale_fail_the_check_naming_each(
    tmp_path: Path,
) -> None:
    (tmp_path / "stale.md").write_text(_STALE, encoding="utf-8")
    (tmp_path / "plain.md").write_text("# Written by hand\n", encoding="utf-8")
    with pytest.raises(GenerateError, match=r"stale\.md are not up to date"):
        check([tmp_path / "plain.md", tmp_path / "stale.md"])


def test_documents_written_anew_pass_the_check_and_keep_what_is_written_by_hand(
    tmp_path: Path,
) -> None:
    path = tmp_path / "stale.md"
    path.write_text(_STALE, encoding="utf-8")
    write([path])
    check([path])
    assert path.read_text(encoding="utf-8").startswith("# Written by hand\n\n<!-- begin")
    assert "### `project.yml`" in path.read_text(encoding="utf-8")


def test_a_document_of_a_generated_part_that_cannot_be_written_is_named(tmp_path: Path) -> None:
    path = tmp_path / "broken.md"
    path.write_text("<!-- begin file: missing.yml -->\n", encoding="utf-8")
    with pytest.raises(GenerateError, match=r"broken\.md: a marker"):
        write([path])


def test_the_generated_parts_of_the_documents_are_up_to_date(
    command_line: Callable[..., int],
) -> None:
    assert command_line(main, "--check") == 0, "uv run scripts/generate.py writes them"
