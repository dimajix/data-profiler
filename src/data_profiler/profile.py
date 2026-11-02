"""The profile: what was found about the tables of one schema of a database.

A profile is what the stages hand to each other, and what a person reads and shares - corrected by
the overrides of the project, laid over it: it holds no values of the columns found sensitive. A
match names its semantic type by its name, of a type of the tool or of the project, whose types the
profile holds in the form `project.yml` gives them, so that it is read without its project.

A profile is a directory of documents, written as YAML in the format below and read back by the
same classes: `profile.yml` holds the profile but its tables, and `tables/` a file of each table,
named after it, so that a person finds a table in a file of its own, and its changes in a diff of
their own. A file of a table is read with the semantic types of `profile.yml`, which its matches
name.

A profile is written by runs of the stage scan. Which profile a scan starts from is decided here, by
`Profile.updating`: the one there is, its run resumed where it did not finish, else in a new run;
each table names the run that counted it, so that a run resumed skips it.
"""

import logging
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Final

from pydantic import PlainSerializer, PlainValidator, TypeAdapter, ValidationInfo
from pydantic_core import PydanticCustomError

from data_profiler.detect import (
    SemanticType,
    SemanticTypeError,
    Sensitivity,
    all_types,
    project_type,
    semantic_type,
)
from data_profiler.documents import DocumentError, read_document, write_document
from data_profiler.files import is_file_name

_logger = logging.getLogger(__name__)

FORMAT: Final = 6
"""The version of the format a profile is written in.

It is raised with every change to the fields of the classes below, or to the files they are
written to: a field added is unknown to the version before, a field removed or renamed is missing
for the version after. A profile of another format is refused, an older one as well: it is removed
and scanned again, not converted.
"""


class ProfileError(Exception):
    """A profile that cannot be read or written: its file, and what is wrong with it."""


# The key of the semantic types of a project in the context of the validation of a document.
_TYPES: Final = "types"
# The file of the profile but its tables, the directory of the files of its tables, and the
# extension of every file of a profile.
_HEAD: Final = "profile.yml"
_TABLES: Final = "tables"
_EXTENSION: Final = ".yml"


@dataclass(frozen=True)
class _Definition:
    """A semantic type of a project, as a document gives it under its name."""

    pattern: str
    sensitivity: Sensitivity


_DEFINITIONS: Final = TypeAdapter(dict[str, _Definition])


def _semantic_types(value: object) -> tuple[SemanticType, ...]:
    """The semantic types of a project that a document gives by `value`, each under its name."""
    definitions = _DEFINITIONS.validate_python(value, extra="forbid")
    try:
        return tuple(
            project_type(name, definition.sensitivity, definition.pattern)
            for name, definition in definitions.items()
        )
    except SemanticTypeError as error:
        raise PydanticCustomError("semantic_type", "{problem}", {"problem": str(error)}) from error


def _definitions(types: tuple[SemanticType, ...]) -> dict[str, dict[str, str]]:
    """`types` as a document gives them, each under its name."""
    return {
        kind.name: {"pattern": kind.detector.pattern.pattern, "sensitivity": kind.sensitivity.value}
        for kind in types
    }


type SemanticTypes = Annotated[
    tuple[SemanticType, ...], PlainValidator(_semantic_types), PlainSerializer(_definitions)
]
"""The semantic types of a project in a document: each under its name, its pattern and sensitivity.

What `detect.project_type` refuses is refused, naming the field.
"""


def _semantic_type(name: object, info: ValidationInfo) -> SemanticType:
    """The semantic type named `name`, of the tool or of the project the document gives."""
    types = info.context.get(_TYPES, ()) if info.context is not None else ()
    kind = semantic_type(name, types) if isinstance(name, str) else None
    if kind is not None:
        return kind
    *others, last = (repr(kind.name) for kind in all_types(types))
    expected = f"{', '.join(others)} or {last}"
    raise PydanticCustomError("semantic_type", "Input should be {expected}", {"expected": expected})


# A semantic type, written by its name.
type _Named = Annotated[
    SemanticType, PlainValidator(_semantic_type), PlainSerializer(lambda kind: kind.name)
]


@dataclass(frozen=True)
class Lengths:
    """The range of the lengths of the values of a text column.

    Attributes:
        shortest: The length of the shortest value, in characters.
        longest: The length of the longest value, in characters.
    """

    shortest: int
    longest: int


@dataclass(frozen=True)
class Range:
    """The smallest and the largest value of a column, as text.

    Attributes:
        smallest: The smallest value, or None where it is withheld, as of a sensitive type.
        largest: The largest value, or None where it is withheld, as of a sensitive type.
    """

    smallest: str | None
    largest: str | None


@dataclass(frozen=True)
class Statistics:
    """What is counted of a column on the whole table.

    Attributes:
        nulls: The number of nulls.
        distinct: The number of distinct values, approximate, as `approx_distinct` counts them.
        lengths: The range of the lengths of the values, or None where none was counted: for a
            column that holds no text, or only nulls.
        range: The range of the values, or None where none is known: for a column whose values
            have no order, that holds only nulls, or that is of a sensitivity.
    """

    nulls: int
    distinct: int
    lengths: Lengths | None = None
    range: Range | None = None


@dataclass(frozen=True)
class Value:
    """A value of an enumeration, as text, with the rows that hold it.

    Attributes:
        value: The value.
        rows: The number of the rows that hold it.
    """

    value: str
    rows: int


@dataclass(frozen=True)
class Match:
    """A semantic type found in a column, with the share of its values that are of it.

    Attributes:
        type: The semantic type.
        sample: The share of the values of the sample, nulls aside, that are of the type, from 0
            to 1.
        table: The share of the values of the whole table, nulls aside, that the pattern of the
            detector of the type matches, from 0 to 1, or None where it was not verified. Where
            the detector checks a value by more than its pattern, it is at least the share the
            check would give; a condition of the column is judged on the sample alone.
    """

    type: _Named
    sample: float
    table: float | None = None


@dataclass(frozen=True)
class Column:
    """A column of a table, under its original name and type, and what was found about it.

    Attributes:
        name: The name of the column in the database.
        type: The type of the column as the database names it, such as `varchar(40)`.
        statistics: What is counted of the column.
        matches: The semantic types found in the column, the most frequent first.
        values: The values of the column, if it is an enumeration of no sensitivity, the most
            frequent first; none else.
        marked: The sensitivity of the column given by hand, by an override, or None where none
            is given.
    """

    name: str
    type: str
    statistics: Statistics
    matches: tuple[Match, ...] = ()
    values: tuple[Value, ...] = ()
    marked: Sensitivity | None = None

    @property
    def sensitivity(self) -> Sensitivity:
        """The sensitivity given by hand, else of its first match of a sensitive type, else none."""
        if self.marked is not None:
            return self.marked
        for match in self.matches:
            if match.type.sensitivity is not Sensitivity.NONE:
                return match.type.sensitivity
        return Sensitivity.NONE

    @property
    def sensitive(self) -> bool:
        """Whether the column is of a sensitivity, so that the profile holds none of its values."""
        return self.sensitivity is not Sensitivity.NONE


@dataclass(frozen=True)
class Table:
    """A table of the schema, under its original name, and what was found about it.

    Attributes:
        name: The name of the table in the database.
        run: When the run of scan that counted the table started, or None where no scan did.
        rows: The number of its rows, counted exactly.
        columns: Its columns, in the order of the table.
    """

    name: str
    # Given by its name, but written after the name, where a person reading the file finds it.
    run: datetime | None = field(default=None, kw_only=True)
    rows: int
    columns: tuple[Column, ...]


@dataclass(frozen=True)
class Run:
    """A run of the stage scan over the selected tables of a profile, which may take several scans.

    A scan begins a run, and a run that did not finish, failing at a table or interrupted, is
    resumed by the next scan; it finishes once every selected table is counted.

    Attributes:
        started: When it started, in UTC; it tells the run apart, and names it in the tables it
            counted.
        finished: When it had counted every selected table, or None while it has not.
    """

    started: datetime
    finished: datetime | None = None


@dataclass(frozen=True)
class Profile:
    """What was found about the tables of one schema of a database.

    Attributes:
        catalog: The catalog of the schema, as Trino names the database it reads.
        schema: The schema whose tables the profile describes.
        tables: The tables that were selected, sorted by their names.
        glossary: Each term of the names of the tables and columns with the word it stands for,
            once proposed or given.
        types: The semantic types of the project the tables were scanned with, beside those of
            the tool.
        run: The last run of scan, or None where no scan wrote the profile.
    """

    catalog: str
    schema: str
    tables: tuple[Table, ...]
    glossary: Mapping[str, str] = field(default_factory=dict)
    types: SemanticTypes = ()
    run: Run | None = None

    @classmethod
    def read(cls, directory: Path) -> "Profile":
        """Reads the profile written to `directory`.

        Args:
            directory: The directory of the profile.

        Returns:
            The profile, its tables sorted by name.

        Raises:
            ProfileError: A file cannot be read, is no YAML, holds no fields, is of another
                format, a field is missing, unknown or of the wrong type, a semantic type of the
                project cannot be made, as `detect.project_type` says, a match names a type
                neither of the tool nor of the project, or the file of a table holds a table of
                another name.
        """
        try:
            head = read_document(directory / _HEAD, _HEAD_ADAPTER, FORMAT)
            tables = [_read_table(path, head.types) for path in _files(directory)]
        except DocumentError as error:
            raise ProfileError(str(error)) from error
        return cls(
            catalog=head.catalog,
            schema=head.schema,
            tables=_sorted(tables),
            glossary=head.glossary,
            types=head.types,
            run=head.run,
        )

    @classmethod
    def updating(
        cls,
        directory: Path,
        catalog: str,
        schema: str,
        types: tuple[SemanticType, ...],
        started: datetime,
    ) -> "Profile":
        """The profile in `directory` that a scan of `schema` of `catalog` with `types` updates.

        A directory without `profile.yml` holds no profile, so that one left by an interrupted
        first write is no profile either. A profile scanned with other semantic types loses its
        tables, as their matches may name a type it no longer has, and keeps its glossary. The run
        of the profile is resumed where it did not finish, and a new run begun else.

        Args:
            directory: The directory of the profile.
            catalog: The catalog of the schema scanned.
            schema: The schema scanned.
            types: The semantic types of the project the scan recognises.
            started: When the scan started, in UTC: the start of a new run, where it begins one.

        Returns:
            The profile in `directory`, without its tables where it was scanned with other types;
            an empty one of `types` where there is none; with its run resumed, or a new one.

        Raises:
            ProfileError: The profile cannot be read, as `read` says, or is of another schema.
        """
        begun = Run(started=started)
        empty = cls(catalog=catalog, schema=schema, tables=(), types=types, run=begun)
        if not (directory / _HEAD).exists():
            return empty
        profile = cls.read(directory)
        if (profile.catalog, profile.schema) != (catalog, schema):
            raise ProfileError(
                f"the profile {directory} is of {profile.catalog}.{profile.schema},"
                f" not of {catalog}.{schema}"
            )
        if profile.types != types:
            _logger.info("The semantic types changed: the tables of %s are scanned anew", directory)
            return replace(empty, glossary=profile.glossary)
        if profile.run is not None and profile.run.finished is None:
            _logger.info("Resuming the scan of %s begun at %s", directory, profile.run.started)
            return profile
        return replace(profile, run=begun)

    def write(self, directory: Path) -> None:
        """Writes the profile to `directory`, each of its files whole or not at all.

        The files of the tables the profile does not have are removed first, then `profile.yml`
        is written, then the tables, so that an interruption leaves no file of a table the profile
        does not have. What it leaves can be read where the types of the profile are those of the
        profile it replaces, or more: a table not yet written again may name any of those.

        Args:
            directory: The directory of the profile, made where it does not exist.

        Raises:
            ProfileError: The name of a table is no name of a file, or a file cannot be written
                or removed.
        """
        for table in self.tables:
            if not is_file_name(table.name):
                raise ProfileError(
                    f"{directory}: the table {table.name!r} has a name that is no name of a file"
                )
        kept = {_file(directory, table.name) for table in self.tables}
        try:
            (directory / _TABLES).mkdir(parents=True, exist_ok=True)
            for path in _files(directory):
                if path not in kept:
                    path.unlink()
        except OSError as error:
            raise ProfileError(f"{directory} cannot be written: {error.strerror}") from error
        head = _Head(
            catalog=self.catalog,
            schema=self.schema,
            run=self.run,
            glossary=self.glossary,
            types=self.types,
        )
        try:
            write_document(directory / _HEAD, _HEAD_ADAPTER, FORMAT, head)
            for table in self.tables:
                write_document(_file(directory, table.name), _TABLE_ADAPTER, FORMAT, table)
        except DocumentError as error:
            raise ProfileError(str(error)) from error

    def updated(self, table: Table) -> "Profile":
        """The profile with `table`, counted by its run, in place of its table of the same name.

        Args:
            table: The table, as it was found anew.

        Returns:
            The profile, `table` in place of its table of the same name, or beside its tables,
            sorted by their names, and named counted by the run of the profile.
        """
        counted = replace(table, run=None if self.run is None else self.run.started)
        others = (kept for kept in self.tables if kept.name != table.name)
        return replace(self, tables=_sorted((*others, counted)))

    def is_counted(self, name: str) -> bool:
        """Whether the profile has the table `name`, counted by the run of the profile.

        Args:
            name: The name of the table.

        Returns:
            True where the table was counted by the run of the profile, False where the profile
            has no run, no table `name`, or one counted by another run.
        """
        return self.run is not None and any(
            table.name == name and table.run == self.run.started for table in self.tables
        )

    def finished(self, at: datetime) -> "Profile":
        """The profile, its run finished, once it has counted every selected table.

        Args:
            at: When the run finished, in UTC.

        Returns:
            The profile, its run finished at `at`; as it is where it has no run.
        """
        if self.run is None:
            return self
        return replace(self, run=replace(self.run, finished=at))

    def restricted(self, names: Collection[str]) -> "Profile":
        """The profile with those of its tables alone that `names` names.

        Args:
            names: The names of the tables to keep.

        Returns:
            The profile, without the tables `names` does not name.
        """
        return replace(self, tables=tuple(table for table in self.tables if table.name in names))


@dataclass(frozen=True)
class _Head:
    """What `profile.yml` holds: the profile but its tables, whose matches name its types."""

    catalog: str
    schema: str
    run: Run | None = None
    glossary: Mapping[str, str] = field(default_factory=dict)
    types: SemanticTypes = ()


def _sorted(tables: Iterable[Table]) -> tuple[Table, ...]:
    """`tables`, sorted by their names, as a profile holds them."""
    return tuple(sorted(tables, key=lambda table: table.name))


def _file(directory: Path, table: str) -> Path:
    """The file of the table named `table` in the profile in `directory`."""
    return directory / _TABLES / f"{table}{_EXTENSION}"


def _files(directory: Path) -> list[Path]:
    """The files of the tables of the profile in `directory`, none where it has no `tables/`."""
    return list((directory / _TABLES).glob(f"*{_EXTENSION}"))


def _read_table(path: Path, types: tuple[SemanticType, ...]) -> Table:
    """The table in the file `path`, whose matches name `types` or those of the tool.

    Raises:
        DocumentError: The file cannot be read as a document of a table.
        ProfileError: The file holds a table of another name than its own.
    """
    table = read_document(path, _TABLE_ADAPTER, FORMAT, {_TYPES: types})
    if table.name != path.name.removesuffix(_EXTENSION):
        raise ProfileError(f"{path} holds the table {table.name!r}, not the one it is named after")
    return table


_HEAD_ADAPTER: Final = TypeAdapter(_Head)
_TABLE_ADAPTER: Final = TypeAdapter(Table)
