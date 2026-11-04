"""Documents: the YAML files a person reads and writes, each of a format of its own.

A document holds the fields of one class, checked by pydantic, and the version of its format in the
field `format`; one with a field missing, unknown or of the wrong type is refused. The field
`format` is the document's own: a class a document holds has none. A field that has its default is
not written: a document holds what differs from the defaults. The validators of a document share a
context, a dict made anew for each document read, by which a field is checked against another that
holds what it names - in the same document, or in another one, whose reader gives what it holds to
begin the context with. The profile is made of such documents, and the configuration of a project
is one.

The version of a format has a major and a minor part. The major version is raised with a change to
the fields of the classes of the format that is incompatible, and the minor version set to 0: a
field added that is required, a field renamed or removed, a default changed - a default is not
written, so that a document of the version before would be read with another value, unseen -, or
the type or the meaning of a field changed. The minor version is raised with a change that is
compatible: a field added that is optional, or a required field made optional. A document of the
major version read and of its minor version or an older one is read, what it lacks taken by its
defaults; one of a newer minor version is refused, as its fields are unknown to the tool, and one
of another major version as well.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from pydantic import TypeAdapter, ValidationError
from yaml import YAMLError, safe_dump, safe_load

from data_profiler.files import write_whole

# A version as a document writes it, a string: YAML would read `13.10` as the number `13.1`.
_VERSION: Final = re.compile(r"(\d+)\.(\d+)")


@dataclass(frozen=True)
class Version:
    """The version of a format, as the module docs say when each of its parts is raised."""

    major: int
    minor: int

    def __str__(self) -> str:
        """The version as a document writes it, `13.1`."""
        return f"{self.major}.{self.minor}"


class DocumentError(Exception):
    """A document that cannot be read or written: its file, and what is wrong with it."""


def read_document[T](
    path: Path,
    adapter: TypeAdapter[T],
    version: Version,
    context: Mapping[str, object] | None = None,
) -> T:
    """The YAML document in `path`, checked by `adapter`, of format `version` or an older minor one.

    What a document of an older minor version lacks takes its default. A version is written as a
    string, `"13.1"`; a plain number, `13`, is read as `"13.0"`.

    Args:
        path: The file of the document.
        adapter: The adapter of the class the document holds.
        version: The version of the format the tool reads: of the same major version, and of this
            minor version or an older one.
        context: What the context of its validators begins with, of another document; nothing
            where none is given.

    Returns:
        What the document holds.

    Raises:
        DocumentError: The file cannot be read, is no YAML, holds no fields, names no version of a
            format, is of another major version or of a newer minor version, or a field is
            missing, unknown or of the wrong type.
    """
    try:
        with path.open(encoding="utf-8") as file:
            content = safe_load(file)
    except OSError as error:
        raise DocumentError(f"{path} cannot be read: {error.strerror}") from error
    except YAMLError as error:
        raise DocumentError(f"{path} is no YAML: {error}") from error
    if not isinstance(content, dict):
        raise DocumentError(f"{path} holds no fields")
    found = content.pop("format", None)
    if found is None:
        raise DocumentError(f"{path} names no format")
    given = _version(path, found)
    if given.major != version.major:
        raise DocumentError(
            f"{path} is of format {given}, of another major version than the format {version} "
            "that is read"
        )
    if given.minor > version.minor:
        raise DocumentError(
            f"{path} is of format {given}, newer than the format {version} that is read: the tool "
            "is older than the document"
        )
    try:
        return adapter.validate_python(content, extra="forbid", context=dict(context or {}))
    except ValidationError as error:
        problems = "; ".join(_problem(detail) for detail in error.errors())
        raise DocumentError(f"{path}: {problems}") from error


def write_document[T](path: Path, adapter: TypeAdapter[T], version: Version, value: T) -> None:
    """Writes `value` to `path` as a YAML document of format `version`, whole or not at all.

    Args:
        path: The file of the document.
        adapter: The adapter of the class of `value`.
        version: The version of the format the document is written in.
        value: What the document is to hold.

    Raises:
        DocumentError: The file cannot be written.
    """
    content = {
        "format": str(version),
        **adapter.dump_python(value, mode="json", exclude_defaults=True),
    }
    try:
        text = safe_dump(content, sort_keys=False, allow_unicode=True)
        write_whole(path, text.encode("utf-8"))
    except OSError as error:
        raise DocumentError(f"{path} cannot be written: {error.strerror}") from error


def _version(path: Path, found: object) -> Version:
    """The version of a format the field `format` of the document in `path` gives as `found`."""
    if type(found) is int:
        return Version(found, 0)
    if isinstance(found, str) and (parts := _VERSION.fullmatch(found)):
        return Version(int(parts[1]), int(parts[2]))
    raise DocumentError(
        f'{path} names the format {found!r}, which is no version of one, written as "1.0"'
    )


def _problem(detail: Any) -> str:
    """The field a detail of a `ValidationError` is about, and what is wrong with it."""
    field = ".".join(str(part) for part in detail["loc"])
    return f"{field}: {detail['msg']}"
