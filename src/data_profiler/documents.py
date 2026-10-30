"""Documents: the YAML files a person reads and writes, each of a format of its own.

A document holds the fields of one class, checked by pydantic, and the version of its format in the
field `format`; a document of another format, or with a field missing, unknown or of the wrong type,
is refused. The field `format` is the document's own: a class a document holds has none. A field
that has its default is not written: a document holds what differs from the defaults.
The profile is such a document, and the configuration of a project.
"""

from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError
from yaml import YAMLError, safe_dump, safe_load

from data_profiler.files import write_whole


class DocumentError(Exception):
    """A document that cannot be read or written: its file, and what is wrong with it."""


def read_document[T](path: Path, adapter: TypeAdapter[T], version: int) -> T:
    """The YAML document in `path`, of format `version`, checked by `adapter`.

    Args:
        path: The file of the document.
        adapter: The adapter of the class the document holds.
        version: The version of the format the document is to be of.

    Returns:
        What the document holds.

    Raises:
        DocumentError: The file cannot be read, is no YAML, holds no fields, is of another format,
            or a field is missing, unknown or of the wrong type.
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
    if type(found) is not int or found != version:
        raise DocumentError(f"{path} is of format {found!r}, but only format {version} is read")
    try:
        return adapter.validate_python(content, extra="forbid")
    except ValidationError as error:
        problems = "; ".join(_problem(detail) for detail in error.errors())
        raise DocumentError(f"{path}: {problems}") from error


def write_document[T](path: Path, adapter: TypeAdapter[T], version: int, value: T) -> None:
    """Writes `value` to `path` as a YAML document of format `version`, whole or not at all.

    Args:
        path: The file of the document.
        adapter: The adapter of the class of `value`.
        version: The version of the format the document is written in.
        value: What the document is to hold.

    Raises:
        DocumentError: The file cannot be written.
    """
    content = {"format": version, **adapter.dump_python(value, mode="json", exclude_defaults=True)}
    try:
        text = safe_dump(content, sort_keys=False, allow_unicode=True)
        write_whole(path, text.encode("utf-8"))
    except OSError as error:
        raise DocumentError(f"{path} cannot be written: {error.strerror}") from error


def _problem(detail: Any) -> str:
    """The field a detail of a `ValidationError` is about, and what is wrong with it."""
    field = ".".join(str(part) for part in detail["loc"])
    return f"{field}: {detail['msg']}"
