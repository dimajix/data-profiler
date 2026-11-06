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

Every attribute of a profile is filled by one step, which replaces in a profile there is those it
fills alone, and keeps all others. The stage scan fills the run and the semantic types of the
profile, the rows, runs, keys, primary keys, groups and discriminators of its tables, and the types,
statistics, matches, values, marks and sentinels of their columns; the stage describe fills the
terms of the names of the tables and columns by its step that splits them, the glossary by its step
that proposes concepts, the readings by its step that reads the names, and the descriptions of the
columns by its step that describes them. The overrides fill none: what they give, the stages lay
over the profile they read - the names given and the descriptions of the database, of the tables and
of the entities among it, which a profile written holds none of -, and scan takes the marks, the
sentinels, the primary keys and the discriminators they give.

A profile is written by runs of the stage scan. Which profile a scan starts from is decided here, by
`Profile.updating`: the one there is, its run resumed where it did not finish, else in a new run;
each table names the run that counted it, so that a run resumed can skip it. A table counted anew
keeps the terms and the readings of its name and of the names of its columns, and the descriptions
of its columns, which describe filled.
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
from data_profiler.documents import DocumentError, Version, read_document, write_document
from data_profiler.files import is_file_name

_logger = logging.getLogger(__name__)

FORMAT: Final = Version(13, 2)
"""The version of the format a profile is written in, raised as `documents` says.

A change to the files the classes below are written to is incompatible as well. A profile of
another major version is removed and scanned again, not converted.
"""


DIGITS: Final = 3
"""The digits a share found in a sample is written with: of a match, and the coherence of a group.

A sample of about 10,000 rows says no more.
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
class Value:
    """A value of an enumeration, or a sentinel, as text, with the rows that hold it.

    Attributes:
        value: The value.
        rows: The number of the rows that hold it.
    """

    value: str
    rows: int


@dataclass(frozen=True)
class Statistics:
    """What is counted of a column on the whole table, its sentinels aside but where counted.

    Attributes:
        nulls: The number of nulls.
        distinct: The number of distinct values, approximate, as `approx_distinct` counts them.
        lengths: The range of the lengths of the values, or None where none was counted: for a
            column that holds no text, or only nulls and sentinels.
        range: The range of the values, or None where none is known: for a column whose values
            have no order, that holds only nulls and sentinels, or that is of a sensitivity.
        sentinels: The values that stand for no value found in the column, its sentinels, each
            with the rows that hold it, the most frequent first; none of a column whose values
            the database writes as no text. They are no values of the column, and shown whatever
            its sensitivity: the sentinels of the tool are fixed, those given are of the overrides.
    """

    nulls: int
    distinct: int
    lengths: Lengths | None = None
    range: Range | None = None
    sentinels: tuple[Value, ...] = ()

    @property
    def sentinel_rows(self) -> int:
        """The number of the rows that hold a sentinel."""
        return sum(sentinel.rows for sentinel in self.sentinels)


@dataclass(frozen=True)
class Match:
    """A semantic type found in a column, with the share of its values that are of it.

    Attributes:
        type: The semantic type.
        sample: The share of the values of the sample, nulls and sentinels aside, that are of the
            type, from 0 to 1.
        table: The share of the values of the whole table, nulls and sentinels aside, that the
            pattern of the detector of the type matches, from 0 to 1, or None where it was not
            verified. Where the detector checks a value by more than its pattern, it is at least
            the share the check would give; a condition of the column is judged on the sample
            alone.
    """

    type: _Named
    sample: float
    table: float | None = None


@dataclass(frozen=True)
class Term:
    """A term of a name, as the vocabulary splits it, with the concepts it may stand for.

    Attributes:
        text: The term, in lower case.
        concepts: The words of the concepts written as it, its candidates, in the order of the
            glossary when it was split; none of a term of digits, which stands for itself, or of a
            term of no concept.
    """

    text: str
    concepts: tuple[str, ...] = ()

    @property
    def candidates(self) -> tuple[str, ...]:
        """What it may be read as: its digits, of a term of digits, else its concepts."""
        return (self.text,) if self.text.isdigit() else self.concepts


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
        sentinels: The sentinels given by hand, by an override, as values, in place of those of
            the tool, that the column was counted with; None where none are given, and where the
            column has no text, which is counted without sentinels, whatever is given.
        terms: The terms of its name, in their order, or None where it is not split yet.
        reading: The reading of its name: the word of the concept each of its terms stands for,
            at its place, the digits of a term of digits; None where it is not read.
        description: What the column holds, in English, for a person who knows the business but
            not the database; None where it is not described.
        name_given: The harmonized name given by hand, by an override, in place of the one composed
            from its reading; None where none is given, and in a profile written.
    """

    name: str
    type: str
    statistics: Statistics
    matches: tuple[Match, ...] = ()
    values: tuple[Value, ...] = ()
    marked: Sensitivity | None = None
    sentinels: tuple[str, ...] | None = None
    terms: tuple[Term, ...] | None = None
    reading: tuple[str, ...] | None = None
    description: str | None = None
    name_given: str | None = None

    @property
    def left_aside(self) -> frozenset[str]:
        """The sentinels its values were counted without: those its statistics found in it."""
        return frozenset(sentinel.value for sentinel in self.statistics.sentinels)

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
class Group:
    """Columns of a table filled together: in mostly the same rows of its sample.

    A column is filled in a row where it holds a value, neither null nor a sentinel. A group holds
    its columns, and a column does not name its group, so that it is said in one place.

    Attributes:
        columns: The names of its columns, at least two, in the order of the table.
        coherence: The mean of the Jaccard indexes of the rows each two of its columns are filled
            in, from 0 to 1, with three digits.
    """

    columns: tuple[str, ...]
    coherence: float


@dataclass(frozen=True)
class Entity:
    """The rows of a table of one entity of the business: those of some values of its discriminator.

    Attributes:
        values: The values of the discriminator its rows hold, as text, the most frequent first.
        rows: The number of its rows.
        filled: The number of its rows each column of the table is filled in - holds a value,
            neither null nor a sentinel -, by the name of the column, of every column of the table
            in its order.
        name_given: Its harmonized name given by hand, by an override; None where none is given,
            and in a profile written.
        description: What it holds, in English, given by hand, by an override; None where none is
            given, and in a profile written.
    """

    values: tuple[str, ...]
    rows: int
    filled: Mapping[str, int]
    name_given: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Discriminator:
    """The column whose values tell the entities of a table apart, and those entities.

    The rows of the table whose discriminator is null or a sentinel are of no entity.

    Attributes:
        column: The name of the column, an enumeration of no sensitivity.
        entities: Its entities, the one of the most rows first, at least two where it is found
            rather than given, and none where it is given of a column that holds no value the
            profile holds; a value is of one entity at most.
        given: The values of each entity the overrides gave, in their order, that it was counted
            with; None where it was found, none given.
    """

    column: str
    entities: tuple[Entity, ...]
    given: tuple[tuple[str, ...], ...] | None = None

    @property
    def rows(self) -> int:
        """The number of the rows of its entities."""
        return sum(entity.rows for entity in self.entities)


@dataclass(frozen=True)
class PrimaryKey:
    """The key that identifies the rows of a table in a data model: chosen, or given by hand.

    Attributes:
        columns: The names of its columns, in the order of the table.
        given: Whether the overrides gave it, rather than it was chosen among the keys; one given
            may be none of them: its values not unique, or holding a key of fewer columns.
    """

    columns: tuple[str, ...]
    given: bool = False


@dataclass(frozen=True)
class Table:
    """A table of the schema, under its original name, and what was found about it.

    Attributes:
        name: The name of the table in the database.
        run: When the run of scan that counted the table started, or None where no scan did.
        rows: The number of its rows, counted exactly.
        columns: Its columns, in the order of the table.
        keys: Its keys: the columns, one or two, whose values together identify each of its rows,
            verified on the whole table, none of them a key of fewer columns; the fewer columns
            first, each in the order of the table.
        primary_key: What identifies its rows in a data model, a key chosen among its keys or the
            columns given; None where it has none.
        groups: The groups of its columns filled together, in the order of their first columns;
            a column is in one group at most.
        discriminator: The column whose values tell the entities of its rows apart, with those
            entities; None where no column does, or the overrides give it none.
        terms: The terms of its name, in their order, or None where it is not split yet.
        reading: The reading of its name: the word of the concept each of its terms stands for,
            at its place, the digits of a term of digits; None where it is not read.
        name_given: The harmonized name given by hand, by an override, in place of the one composed
            from its reading; None where none is given, and in a profile written.
        description: What the table holds, in English, given by hand, by an override; None where
            none is given, and in a profile written.
    """

    name: str
    # Given by its name, but written after the name, where a person reading the file finds it.
    run: datetime | None = field(default=None, kw_only=True)
    rows: int
    columns: tuple[Column, ...]
    keys: tuple[tuple[str, ...], ...] = ()
    primary_key: PrimaryKey | None = None
    groups: tuple[Group, ...] = ()
    discriminator: Discriminator | None = None
    terms: tuple[Term, ...] | None = None
    reading: tuple[str, ...] | None = None
    name_given: str | None = None
    description: str | None = None

    def column(self, name: str) -> Column:
        """Its column of the name `name`.

        Args:
            name: The name of the column in the database.

        Returns:
            The column.

        Raises:
            KeyError: The table has no column of the name, which a caller that names one makes
                sure of.
        """
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(name)


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
class Concept:
    """An entry of the glossary: what a word means, and the terms it is written as in the names.

    An abbreviation may be of several concepts, which a term of a name may each stand for.

    Attributes:
        abbreviations: The terms it is written as beside its word, in lower case, none where none
            is given; its word is a term of it where it is one, as `glossary.written_as` tells.
        description: What it means, in English; None where none is given.
        omitted: Whether it is left out of harmonized names, as a prefix that marks a custom
            column, which says nothing of what the column holds.
    """

    abbreviations: tuple[str, ...] = ()
    description: str | None = None
    omitted: bool = False


@dataclass(frozen=True)
class Profile:
    """What was found about the tables of one schema of a database.

    Attributes:
        catalog: The catalog of the schema, as Trino names the database it reads.
        schema: The schema whose tables the profile describes.
        tables: The tables that were selected, sorted by their names.
        glossary: The concepts of the names of the tables and columns, by their words, once
            proposed or given.
        types: The semantic types of the project the tables were scanned with, beside those of
            the tool.
        run: The last run of scan, or None where no scan wrote the profile.
        description: What the database holds, in English, given by hand, by an override; None
            where none is given, and in a profile written.
    """

    catalog: str
    schema: str
    tables: tuple[Table, ...]
    glossary: Mapping[str, Concept] = field(default_factory=dict)
    types: SemanticTypes = ()
    run: Run | None = None
    description: str | None = None

    @classmethod
    def read(cls, directory: Path) -> "Profile":
        """Reads the profile written to `directory`.

        Args:
            directory: The directory of the profile.

        Returns:
            The profile, its tables sorted by name.

        Raises:
            ProfileError: A file cannot be read, is no YAML, holds no fields, names no version
                of a format, is of another major version or of a newer minor version, a field is
                missing, unknown or of the wrong type, a semantic type of the project cannot be
                made, as `detect.project_type` says, a match names a type neither of the tool
                nor of the project, the file of a table holds a table of another name, the groups
                of a table name a column it does not have, or one twice, or its discriminator
                names a column it does not have, an entity of it not the filled rows of each
                column, or two entities the same value.
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
            description=head.description,
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
        first write is no profile either. A profile scanned with other semantic types keeps its
        tables, but their matches, which may name a type it no longer has, and the values and
        ranges of their columns, which a type it has now may find sensitive, until they are
        counted anew, and the discriminators of the tables, whose values are values of their
        columns; its glossary and what describe filled it keeps as well. The run of the
        profile is resumed where it did not finish, and a new run begun else.

        Args:
            directory: The directory of the profile.
            catalog: The catalog of the schema scanned.
            schema: The schema scanned.
            types: The semantic types of the project the scan recognises.
            started: When the scan started, in UTC: the start of a new run, where it begins one.

        Returns:
            The profile in `directory`, its tables without their matches, values, ranges and
            discriminators where it was scanned with other types, then in a new run; an empty one
            of `types` where there is none; with its run resumed, or a new one.

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
            tables = tuple(_unmatched(table) for table in profile.tables)
            return replace(profile, tables=tables, types=types, run=begun)
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
            description=self.description,
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
            table: The table, as scan found it anew.

        Returns:
            The profile, `table` in place of its table of the same name, or beside its tables,
            sorted by their names, and named counted by the run of the profile; with the terms and
            readings of its table of the same name and of its columns of the same names, and the
            descriptions of those columns.
        """
        counted = replace(table, run=None if self.run is None else self.run.started)
        for kept in self.tables:
            if kept.name == table.name:
                counted = _described(counted, kept)
        others = (kept for kept in self.tables if kept.name != table.name)
        return replace(self, tables=_sorted((*others, counted)))

    def counted(self, name: str) -> Table | None:
        """The table `name`, where the run of the profile counted it.

        Args:
            name: The name of the table.

        Returns:
            The table, where the run of the profile counted it; None where the profile has no run,
            no table `name`, or one counted by another run.
        """
        if self.run is None:
            return None
        started = self.run.started
        found = (table for table in self.tables if table.name == name and table.run == started)
        return next(found, None)

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
    glossary: Mapping[str, Concept] = field(default_factory=dict)
    types: SemanticTypes = ()
    description: str | None = None


def _unmatched(table: Table) -> Table:
    """`table` without its discriminator, its columns without their matches, values and ranges."""
    columns = (
        replace(column, matches=(), values=(), statistics=replace(column.statistics, range=None))
        for column in table.columns
    )
    return replace(table, columns=tuple(columns), discriminator=None)


def _described(table: Table, kept: Table) -> Table:
    """`table`, with what describe filled of `kept`, of its name and of its columns of a name."""
    described = {column.name: column for column in kept.columns}
    columns = (
        replace(column, terms=old.terms, reading=old.reading, description=old.description)
        if (old := described.get(column.name)) is not None
        else column
        for column in table.columns
    )
    return replace(table, columns=tuple(columns), terms=kept.terms, reading=kept.reading)


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
        ProfileError: The file holds a table of another name than its own, a key, the primary
            key or a group names a column the table does not have, or the groups name one twice,
            or the discriminator is not one of the table, as `_refuse_discriminator` says.
    """
    table = read_document(path, _TABLE_ADAPTER, FORMAT, {_TYPES: types})
    if table.name != path.name.removesuffix(_EXTENSION):
        raise ProfileError(f"{path} holds the table {table.name!r}, not the one it is named after")
    names = {column.name for column in table.columns}
    primary = () if table.primary_key is None else table.primary_key.columns
    _refuse_unknown(path, "a key", [name for key in (*table.keys, primary) for name in key], names)
    grouped = [name for group in table.groups for name in group.columns]
    _refuse_unknown(path, "a group", grouped, names)
    twice = next((name for name in grouped if grouped.count(name) > 1), None)
    if twice is not None:
        raise ProfileError(f"{path}: the groups name the column {twice!r} twice")
    if table.discriminator is not None:
        _refuse_discriminator(path, table.discriminator, names)
    return table


def _refuse_unknown(path: Path, naming: str, named: Iterable[str], names: Collection[str]) -> None:
    """Refuses `named`, the columns `naming` names, where one is not of the columns `names`.

    Raises:
        ProfileError: A column of `named` is not of `names`, the first such named.
    """
    unknown = next((name for name in named if name not in names), None)
    if unknown is not None:
        raise ProfileError(
            f"{path}: {naming} names the column {unknown!r}, which the table does not have"
        )


def _refuse_discriminator(path: Path, discriminator: Discriminator, names: Collection[str]) -> None:
    """Refuses `discriminator` where it is not one of a table of the columns `names`.

    Raises:
        ProfileError: The discriminator names a column not of `names`, an entity gives the filled
            rows of other columns than those of `names`, or two entities name the same value.
    """
    _refuse_unknown(path, "the discriminator", [discriminator.column], names)
    if any(set(entity.filled) != set(names) for entity in discriminator.entities):
        raise ProfileError(f"{path}: an entity does not give the filled rows of each column")
    # The values are not named: they are values of the database, which no message holds.
    values: set[str] = set()
    for entity in discriminator.entities:
        for value in entity.values:
            if value in values:
                raise ProfileError(f"{path}: the discriminator names a value of two entities")
            values.add(value)


_HEAD_ADAPTER: Final = TypeAdapter(_Head)
_TABLE_ADAPTER: Final = TypeAdapter(Table)
