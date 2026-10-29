"""The workspace: the local directory of samples and intermediate results of the stages.

It may hold values of the database, and never leaves the machine: it keeps itself out of version
control by a `.gitignore` of its own, wherever it lies. A workspace belongs to one schema, as a
profile does: the file `schema` names it, and a workspace is not opened for another, whose tables
of the same names would overwrite its own. The sample of a table is kept as Parquet in `samples/`,
written whole or not at all.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Final, Self

from pyarrow import ArrowException
from pyarrow import Table as ArrowTable
from pyarrow.parquet import read_table, write_table

from data_profiler.files import write_whole

# What keeps the workspace out of version control: everything in it.
_IGNORED: Final = b"# The workspace of data-profiler, which may hold values of the database.\n*\n"


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
            schema: The schema whose tables the workspace holds samples of.

        Returns:
            The workspace.

        Raises:
            WorkspaceError: The directory cannot be made, or it is the workspace of another schema.
        """
        owner = f"{catalog}.{schema}"
        named = path / "schema"
        try:
            (path / "samples").mkdir(parents=True, exist_ok=True)
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
        path = self._sample(table)
        buffer = BytesIO()
        try:
            write_table(ArrowTable.from_pydict(dict(sample.columns)), buffer)
        except ArrowException as error:
            # What pyarrow says names the values it could not convert; they stay in the cause.
            raise WorkspaceError(
                f"the sample of {table} holds values of different kinds"
            ) from error
        try:
            write_whole(path, buffer.getvalue())
        except OSError as error:
            raise WorkspaceError(
                f"the sample {path} cannot be written: {error.strerror}"
            ) from error

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
        path = self._sample(table)
        if not path.exists():
            raise WorkspaceError(f"the workspace {self._path} holds no sample of {table}")
        try:
            columns = read_table(path).to_pydict()
        except (OSError, ArrowException) as error:
            raise WorkspaceError(f"the sample {path} cannot be read") from error
        return Sample(columns=columns)

    def _sample(self, table: str) -> Path:
        """The file of the sample of `table`, refused where the name would leave `samples/`."""
        if not table or table.startswith(".") or "/" in table or "\\" in table:
            raise WorkspaceError(f"the table {table!r} has a name that is no name of a file")
        return self._path / "samples" / f"{table}.parquet"
