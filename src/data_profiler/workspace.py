"""The workspace: the local directory of samples and intermediate results of the stages.

It may hold values of the database, and never leaves the machine: it keeps itself out of version
control by a `.gitignore` of its own, wherever it lies. A workspace belongs to one schema, as a
profile does: the file `schema` names it, and a workspace is not opened for another, whose tables
of the same names would overwrite its own. Of each table, its sample is kept as Parquet in
`samples/`, and its enumerations in `enumerations/`, all of a table in one file: one column for
each, of one row, the list of its values with their rows. Each file is written whole or not at
all, so that the enumerations of a table never mix with those of an earlier scan.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any, Final, Self

from pyarrow import ArrowException
from pyarrow import Table as ArrowTable
from pyarrow.parquet import read_table, write_table

from data_profiler.files import write_whole

# What keeps the workspace out of version control: everything in it.
_IGNORED: Final = b"# The workspace of data-profiler, which may hold values of the database.\n*\n"


class _Kind(Enum):
    """What a file of the workspace holds: its directory, and its noun in the messages."""

    SAMPLE = ("samples", "sample")
    ENUMERATIONS = ("enumerations", "enumerations")

    def __init__(self, directory: str, noun: str) -> None:
        """Takes the directory of the files of the kind, one per table, and its noun."""
        self.directory = directory
        self.noun = noun


class WorkspaceError(Exception):
    """A workspace that cannot be made, written or read: its file, and what is wrong."""


@dataclass(frozen=True)
class Sample:
    """Rows taken from a table at random.

    Attributes:
        columns: The values of each column, by its name, in the order of the table; None is a
            null.
    """

    columns: Mapping[str, Sequence[object]]


@dataclass(frozen=True)
class Enumeration:
    """A column of few distinct values, each with the rows that hold it.

    Attributes:
        column: The name of the column.
        values: Each value of the column but null, with the number of rows that hold it, the most
            frequent first.
    """

    column: str
    values: tuple[tuple[object, int], ...]


class Workspace:
    """A directory of samples and intermediate results, one file per table and kind."""

    def __init__(self, path: Path) -> None:
        """Takes the directory of the workspace, which `open` has made."""
        self._path = path

    @classmethod
    def open(cls, path: Path, catalog: str, schema: str) -> Self:
        """The workspace of `schema` of `catalog` in `path`, made where it does not exist.

        Its `.gitignore` is written where there is none, and left as it is where there is one.

        Args:
            path: The directory of the workspace.
            catalog: The catalog of the schema.
            schema: The schema whose tables the workspace holds.

        Returns:
            The workspace.

        Raises:
            WorkspaceError: The directory cannot be made, or it is the workspace of another schema.
        """
        owner = f"{catalog}.{schema}"
        named = path / "schema"
        try:
            for kind in _Kind:
                (path / kind.directory).mkdir(parents=True, exist_ok=True)
            ignored = path / ".gitignore"
            if not ignored.exists():
                write_whole(ignored, _IGNORED)
            if not named.exists():
                write_whole(named, f"{owner}\n".encode())
            found = named.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise WorkspaceError(
                f"the workspace {path} cannot be made: {error.strerror}"
            ) from error
        if found != owner:
            raise WorkspaceError(f"the workspace {path} is of {found}, not of {owner}")
        return cls(path)

    def write_sample(self, table: str, sample: Sample) -> None:
        """Writes the sample of `table`, whole or not at all.

        Args:
            table: The name of the table the sample was taken of.
            sample: The sample.

        Raises:
            WorkspaceError: The name of the table is no name of a file, the values of a column
                cannot be written together, or the file cannot be written.
        """
        self._write(_Kind.SAMPLE, table, sample.columns)

    def read_sample(self, table: str) -> Sample:
        """The sample of `table`.

        Args:
            table: The name of the table the sample was taken of.

        Returns:
            The sample.

        Raises:
            WorkspaceError: The name of the table is no name of a file, there is no sample of it,
                or the sample cannot be read.
        """
        return Sample(columns=self._read(_Kind.SAMPLE, table))

    def write_enumerations(self, table: str, enumerations: Sequence[Enumeration]) -> None:
        """Writes the enumerations of `table`, whole or not at all, in place of earlier ones.

        Args:
            table: The name of the table the enumerations are columns of.
            enumerations: The enumerations, in the order of the table; none where it has none.

        Raises:
            WorkspaceError: The name of the table is no name of a file, the values of an
                enumeration cannot be written together, or the file cannot be written.
        """
        columns = {
            enumeration.column: [
                [{"value": value, "rows": rows} for value, rows in enumeration.values]
            ]
            for enumeration in enumerations
        }
        self._write(_Kind.ENUMERATIONS, table, columns)

    def read_enumerations(self, table: str) -> list[Enumeration]:
        """The enumerations of `table`, in the order of the table.

        Args:
            table: The name of the table the enumerations are columns of.

        Returns:
            The enumerations.

        Raises:
            WorkspaceError: The name of the table is no name of a file, its enumerations were not
                counted, or they cannot be read.
        """
        columns = self._read(_Kind.ENUMERATIONS, table)
        try:
            return [
                Enumeration(
                    column=column,
                    values=tuple((value["value"], value["rows"]) for value in values),
                )
                for column, (values,) in columns.items()
            ]
        except (ValueError, KeyError, TypeError) as error:
            path = self._file(_Kind.ENUMERATIONS, table)
            raise WorkspaceError(
                f"the enumerations of {table} in {path} are not of the form they are written in"
            ) from error

    def _write(self, kind: _Kind, table: str, columns: Mapping[str, Sequence[object]]) -> None:
        """Writes `columns` as the file of `kind` of `table`, whole or not at all.

        Args:
            kind: What the file holds.
            table: The name of the table.
            columns: The values of each column of the file, by its name.

        Raises:
            WorkspaceError: The name of the table is no name of a file, the values of a column
                cannot be written together, or the file cannot be written.
        """
        path = self._file(kind, table)
        buffer = BytesIO()
        try:
            write_table(ArrowTable.from_pydict(dict(columns)), buffer)
        except ArrowException as error:
            # What pyarrow says names the values it could not convert; they stay in the cause.
            raise WorkspaceError(
                f"the {kind.noun} of {table} cannot be written: "
                "values of different kinds in a column"
            ) from error
        try:
            write_whole(path, buffer.getvalue())
        except OSError as error:
            raise WorkspaceError(
                f"the {kind.noun} of {table} cannot be written to {path}: {error.strerror}"
            ) from error

    def _read(self, kind: _Kind, table: str) -> dict[str, list[Any]]:
        """The columns of the file of `kind` of `table`, by their names.

        Raises:
            WorkspaceError: The name of the table is no name of a file, there is no such file, or
                it cannot be read.
        """
        path = self._file(kind, table)
        if not path.exists():
            raise WorkspaceError(f"the workspace {self._path} holds no {kind.noun} of {table}")
        try:
            return read_table(path).to_pydict()
        except (OSError, ArrowException) as error:
            raise WorkspaceError(
                f"the {kind.noun} of {table} cannot be read from {path}"
            ) from error

    def _file(self, kind: _Kind, table: str) -> Path:
        """The file of `kind` of `table`, refused where the name would leave its directory."""
        if not table or table.startswith(".") or "/" in table or "\\" in table:
            raise WorkspaceError(f"the table {table!r} has a name that is no name of a file")
        return self._path / kind.directory / f"{table}.parquet"
