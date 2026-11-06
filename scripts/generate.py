"""Generate: the parts of the documents in `docs/` that are written from the code and other files.

    uv run scripts/generate.py [--debug] [--check]

A generated part stands between two markers, which name what it holds, and is written anew from
what they name:

*   `<!-- begin reference: overrides.yml -->` and `<!-- end reference: overrides.yml -->` - the
    reference of the format of a document, of `project.yml`, `overrides.yml`, `profile.yml` or
    `tables/<table>.yml`: of the class it holds and of every class within it, its description and a
    table of its fields, each with its type, its default and its description, taken from the
    `Attributes:` of the doc comment of the class. A field without a description, and a type the
    reference does not know, fail the run, so that the reference never holds less than the format.
*   `<!-- begin file: examples/crm/overrides.yml -->` and `<!-- end file: … -->` - a file of the
    repository, in a code block of YAML, as it is.

Everything outside the markers is written by hand, and left as it is; a marker without its partner
fails the run. With `--check` nothing is written: the run fails where a document is not what it
would write. `data_profiler.commands.run` configures the log and ends the program when the run
fails.
"""

import dataclasses
import inspect
import logging
import re
import typing
from argparse import ArgumentParser
from collections.abc import Mapping
from dataclasses import MISSING, Field
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Annotated, Any, Final, Literal, TypeAliasType, Union

from pydantic import BeforeValidator, PlainValidator, WrapValidator
from pydantic_core import PydanticUndefined

from data_profiler import overrides, project
from data_profiler.commands import run
from data_profiler.documents import Format
from data_profiler.profile import HEAD_FORMAT, TABLE_FORMAT

_logger = logging.getLogger(__name__)

# The directory of the repository, which the files of the markers are named from.
_TOP: Final = Path(__file__).parent.parent
# The formats a marker of a reference names, by the files of their documents.
_FORMATS: Final[Mapping[str, Format[Any]]] = {
    "project.yml": project.FORMAT,
    "overrides.yml": overrides.FORMAT,
    "profile.yml": HEAD_FORMAT,
    "tables/<table>.yml": TABLE_FORMAT,
}
# A marker, and a generated part: its markers, what they name, and what stands between them.
_MARKER: Final = re.compile(r"^<!-- (begin|end) (reference|file): \S+ -->$", re.MULTILINE)
_PART: Final = re.compile(
    r"^<!-- begin (?P<kind>reference|file): (?P<name>\S+) -->\n"
    r".*?^<!-- end (?P=kind): (?P=name) -->$",
    re.MULTILINE | re.DOTALL,
)
# The section of the fields of a class in its doc comment, and a field in it with the first line of
# its description; the lines after it are indented further.
_ATTRIBUTES: Final = re.compile(r"^Attributes:\n(?P<fields>(?:(?: {4}.*)?\n?)*)", re.MULTILINE)
_FIELD: Final = re.compile(r" {4}(?P<name>\w+): (?P<text>.*)")
# The validators that read what a document gives before the type does, or in its place, of the type
# they name; an `AfterValidator` checks the type once it is read.
_READERS: Final = (PlainValidator, BeforeValidator, WrapValidator)
# The words of the types of values, as YAML writes them.
_SCALARS: Final[Mapping[object, str]] = {
    str: "text",
    int: "integer",
    float: "number",
    bool: "boolean",
    datetime: "timestamp",
}


class GenerateError(Exception):
    """A generated part that cannot be written, or is not what would be written."""


def reference(file: str, format: Format[Any]) -> str:
    """The reference of `format`, the format of the document `file`, as Markdown.

    The class the document holds comes first, under a heading of `file`, then every class within
    it, each under a heading of its name, in the order they are first named.

    Args:
        file: The file of the document, as a person names it.
        format: Its format.

    Returns:
        The reference, of the class of the document and every class within it.

    Raises:
        GenerateError: A class has no `Attributes:`, a field has no description, or a type or a
            default is not known; the message names the class and the field.
    """
    sections = []
    pending: list[type] = [format.root]
    done: set[type] = set()
    while pending:
        kind = pending.pop(0)
        if kind in done:
            continue
        done.add(kind)
        if kind is format.root:
            heading = f"### `{file}`"
            begins = f'The document begins with `format: "{format.version}"`, its version.\n\n'
        else:
            heading = f"#### {_name(kind)}"
            begins = ""
        sections.append(f"{heading}\n\n{begins}{_described(kind, pending)}")
    return "\n\n".join(sections)


def generated(text: str) -> str:
    """`text`, a document, with each of its generated parts written anew.

    Args:
        text: The document.

    Returns:
        The document, the generated parts written anew, the rest as it is.

    Raises:
        GenerateError: A marker has no partner, names a format not known or a file that cannot be
            read, or a reference cannot be written, as `reference` says.
    """
    if 2 * len(_PART.findall(text)) != len(_MARKER.findall(text)):
        raise GenerateError("a marker of a generated part has no partner, or one of another name")

    def part(match: re.Match[str]) -> str:
        kind, name = match["kind"], match["name"]
        if kind == "reference":
            found = _FORMATS.get(name)
            if found is None:
                raise GenerateError(f"no format of {name} is known; known: {', '.join(_FORMATS)}")
            content = reference(name, found)
        else:
            try:
                content = f"```yaml\n{(_TOP / name).read_text(encoding='utf-8')}```"
            except OSError as error:
                raise GenerateError(f"{name} cannot be read: {error.strerror}") from error
        return f"<!-- begin {kind}: {name} -->\n{content}\n<!-- end {kind}: {name} -->"

    return _PART.sub(part, text)


def write(directory: Path) -> None:
    """Writes the generated parts of the documents in `directory` anew, those that differ.

    Args:
        directory: The directory of the documents, Markdown files.

    Raises:
        GenerateError: A document cannot be read or written, or its generated parts cannot be
            written, as `generated` says; the message names the document.
    """
    for path, written in _stale(directory).items():
        try:
            path.write_text(written, encoding="utf-8")
        except OSError as error:
            raise GenerateError(f"{path} cannot be written: {error.strerror}") from error
        _logger.info("%s written", path)


def check(directory: Path) -> None:
    """Checks that the generated parts of the documents in `directory` are what would be written.

    Args:
        directory: The directory of the documents, Markdown files.

    Raises:
        GenerateError: A document is not what would be written, naming each, or cannot be read, or
            its generated parts cannot be written, as `generated` says.
    """
    stale = [str(path) for path in _stale(directory)]
    if stale:
        raise GenerateError(
            f"the generated parts of {', '.join(stale)} are not up to date; they are written by"
            " `uv run scripts/generate.py`"
        )


def main() -> None:
    """Writes the generated parts of the documents in `docs/` anew, or checks them by `--check`."""
    parser = ArgumentParser(prog="generate", description="The generated parts of the documents.")
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    parser.add_argument("--check", action="store_true", help="write nothing, fail where not equal")
    arguments = parser.parse_args()
    act = check if arguments.check else write
    run(lambda: act(_TOP / "docs"), arguments.debug, (GenerateError,))


def _stale(directory: Path) -> dict[Path, str]:
    """The documents in `directory` whose generated parts differ, each as it would be written."""
    stale = {}
    for path in sorted(directory.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
            written = generated(text)
        except OSError as error:
            raise GenerateError(f"{path} cannot be read: {error.strerror}") from error
        except GenerateError as error:
            raise GenerateError(f"{path}: {error}") from error
        if written != text:
            stale[path] = written
    return stale


def _described(kind: type, pending: list[type]) -> str:
    """The description and the table of the fields of the class `kind`, its classes to `pending`."""
    doc = inspect.getdoc(kind) or ""
    described = _descriptions(kind, doc)
    text = doc.split("\nAttributes:\n")[0].strip()
    hints = typing.get_type_hints(kind, include_extras=True)
    rows = ["| Field | Type | Default | Description |", "|---|---|---|---|"]
    for field in dataclasses.fields(kind):
        try:
            if field.name not in described:
                raise GenerateError("it has no description")
            default = _default(field)
            written = _type(hints[field.name], pending)
        except GenerateError as error:
            raise GenerateError(f"the field {kind.__name__}.{field.name}: {error}") from error
        if default == "required" and type(None) in typing.get_args(hints[field.name]):
            # A field required that may be None is written `null`, not left out.
            written += " or `null`"
        description = described[field.name].replace("|", "\\|")
        rows.append(f"| `{field.name}` | {written} | {default} | {description} |")
    return f"{text}\n\n" + "\n".join(rows)


def _descriptions(kind: type, doc: str) -> dict[str, str]:
    """The descriptions of the fields of the class `kind`, of its doc comment `doc`, by name."""
    section = _ATTRIBUTES.search(doc)
    if section is None:
        raise GenerateError(f"the doc comment of {kind.__name__} has no Attributes:")
    found: dict[str, str] = {}
    name = None
    for line in section["fields"].splitlines():
        if field := _FIELD.fullmatch(line):
            name = field["name"]
            found[name] = field["text"]
        elif name is not None and line.strip():
            found[name] += f" {line.strip()}"
    return found


def _type(hint: object, pending: list[type]) -> str:
    """The type `hint` of a field, as the reference writes it; its classes added to `pending`."""
    if isinstance(hint, TypeAliasType):
        return _type(hint.__value__, pending)
    origin = typing.get_origin(hint)
    arguments = typing.get_args(hint)
    if origin is None:
        return _plain(hint, pending)
    if origin is Annotated:
        # A type of a validator that reads what it is given is written as the validator reads it;
        # one checked once it is read, as the type it is read as.
        validator = next((item for item in arguments[1:] if isinstance(item, _READERS)), None)
        if validator is None:
            return _type(arguments[0], pending)
        if validator.json_schema_input_type in (Any, PydanticUndefined):
            raise GenerateError(f"its type {hint} names no json_schema_input_type")
        return _type(validator.json_schema_input_type, pending)
    if origin in (UnionType, Union):
        return " or ".join(_type(item, pending) for item in arguments if item is not type(None))
    if origin is Literal:
        return " or ".join(f"`{str(item).lower()}`" for item in arguments)
    if origin is tuple:
        return f"list of {_type(arguments[0], pending)}"
    if origin in (Mapping, dict):
        return f"map of {_type(arguments[1], pending)}"
    raise GenerateError(f"its type {hint} is not known to the reference")


def _plain(hint: object, pending: list[type]) -> str:
    """The type `hint` of no arguments, as the reference writes it; a class added to `pending`."""
    if isinstance(hint, type) and issubclass(hint, Enum):
        *others, last = (f"`{member.value}`" for member in hint)
        return f"{', '.join(others)} or {last}"
    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        pending.append(hint)
        return f"[{_name(hint)}](#{_name(hint).lower()})"
    if hint in _SCALARS:
        return _SCALARS[hint]
    raise GenerateError(f"its type {hint} is not known to the reference")


def _default(field: Field[Any]) -> str:
    """The default of `field`, as the reference writes it: required, where it has none."""
    if field.default is not MISSING:
        value = field.default
    elif field.default_factory is not MISSING:
        value = field.default_factory()
    else:
        return "required"
    if value is None:
        return "absent"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if value in ((), {}):
        return "empty"
    raise GenerateError(f"its default {value!r} is not known to the reference")


def _name(kind: type) -> str:
    """The name of the class `kind` in the reference: its name, without an underscore."""
    return kind.__name__.lstrip("_")


if __name__ == "__main__":
    main()
