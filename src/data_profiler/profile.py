"""The profile: what was found about the tables of one schema of a database.

A profile is what the stages hand to each other, and what a person reads, shares and corrects: it
holds no sensitive values. It is written as YAML, with the version of its format in the field
`format`, and read back by the same classes; a profile of another format, or with a field missing,
unknown or of the wrong type, is refused.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from pydantic import ConfigDict, TypeAdapter, ValidationError, with_config
from yaml import YAMLError, safe_dump, safe_load

FORMAT: Final = 1
"""The version of the format a profile is written in.

It is raised with every change to the fields of the classes below: a field added is unknown to the
version before, a field removed or renamed is missing for the version after. A profile of another
format is refused; whether older formats are read again is decided when the format first changes.
"""

# A field a class does not know is refused, not passed over.
_STRICT: Final = ConfigDict(extra="forbid")


class ProfileError(Exception):
    """A profile that cannot be read or written: its file, and what is wrong with it."""


@with_config(_STRICT)
@dataclass(frozen=True)
class Lengths:
    """The range of the lengths of the values of a text column.

    Attributes:
        shortest: The length of the shortest value, in characters.
        longest: The length of the longest value, in characters.
    """

    shortest: int
    longest: int


@with_config(_STRICT)
@dataclass(frozen=True)
class Statistics:
    """What is counted of a column on the whole table.

    Attributes:
        nulls: The number of nulls.
        distinct: The number of distinct values, approximate, as `approx_distinct` counts them.
        lengths: The range of the lengths of the values, or None where none was counted: for a
            column that holds no text, or only nulls.
    """

    nulls: int
    distinct: int
    lengths: Lengths | None = None


@with_config(_STRICT)
@dataclass(frozen=True)
class Column:
    """A column of a table, under its original name and type, and what was found about it.

    Attributes:
        name: The name of the column in the database.
        type: The type of the column as the database names it, such as `varchar(40)`.
        statistics: What is counted of the column.
    """

    name: str
    type: str
    statistics: Statistics


@with_config(_STRICT)
@dataclass(frozen=True)
class Table:
    """A table of the schema, under its original name, and what was found about it.

    Attributes:
        name: The name of the table in the database.
        rows: The number of its rows, counted exactly.
        columns: Its columns, in the order of the table.
    """

    name: str
    rows: int
    columns: tuple[Column, ...]


@with_config(_STRICT)
@dataclass(frozen=True)
class Profile:
    """What was found about the tables of one schema of a database.

    Attributes:
        catalog: The catalog of the schema, as Trino names the database it reads.
        schema: The schema whose tables the profile describes.
        tables: The tables that were selected, by their names.
    """

    catalog: str
    schema: str
    tables: tuple[Table, ...]

    @classmethod
    def read(cls, path: Path) -> "Profile":
        """Reads the profile written to `path`.

        Args:
            path: The file of the profile.

        Returns:
            The profile.

        Raises:
            ProfileError: The file cannot be read, is no YAML, is of another format, or a field
                is missing, unknown or of the wrong type.
        """
        try:
            with path.open(encoding="utf-8") as file:
                content = safe_load(file)
        except OSError as error:
            raise ProfileError(f"{path} cannot be read: {error.strerror}") from error
        except YAMLError as error:
            raise ProfileError(f"{path} is no YAML: {error}") from error
        if not isinstance(content, dict):
            raise ProfileError(f"{path} holds no profile")
        version = content.pop("format", None)
        if version is None:
            raise ProfileError(f"{path} names no format")
        if type(version) is not int or version != FORMAT:
            raise ProfileError(f"{path} is of format {version!r}, but only format {FORMAT} is read")
        try:
            return _ADAPTER.validate_python(content)
        except ValidationError as error:
            problems = "; ".join(_problem(detail) for detail in error.errors())
            raise ProfileError(f"{path}: {problems}") from error

    def write(self, path: Path) -> None:
        """Writes the profile to `path`, whole or not at all.

        Args:
            path: The file of the profile.

        Raises:
            ProfileError: The file cannot be written.
        """
        content = {"format": FORMAT, **_ADAPTER.dump_python(self, mode="json", exclude_none=True)}
        try:
            _replace(path, safe_dump(content, sort_keys=False, allow_unicode=True))
        except OSError as error:
            raise ProfileError(f"{path} cannot be written: {error.strerror}") from error


_ADAPTER: Final = TypeAdapter(Profile)


def _problem(detail: Any) -> str:
    """The field a detail of a `ValidationError` is about, and what is wrong with it."""
    field = ".".join(str(part) for part in detail["loc"])
    return f"{field}: {detail['msg']}"


def _replace(path: Path, text: str) -> None:
    """Replaces the file `path` by `text`, whole or not at all.

    The text is written to a new file next to `path`, which then takes its place, so that a
    failure, or an interruption, leaves the file that was there before. The new file is made as
    any file is, with the permissions the user gives new files.

    Raises:
        OSError: The file cannot be written.
    """
    temporary = path.with_name(f".{path.name}.{uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8") as file:
            file.write(text)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
