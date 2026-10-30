"""The profile: what was found about the tables of one schema of a database.

A profile is what the stages hand to each other, and what a person reads, shares and corrects: it
holds no values of the columns found sensitive. It is a document, written as YAML in the format
below and read back by the same classes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.documents import DocumentError, read_document, write_document

FORMAT: Final = 2
"""The version of the format a profile is written in.

It is raised with every change to the fields of the classes below: a field added is unknown to the
version before, a field removed or renamed is missing for the version after. A profile of another
format is refused; whether older formats are read again is decided when the format first changes.
"""


class ProfileError(Exception):
    """A profile that cannot be read or written: its file, and what is wrong with it."""


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
            the detector checks more than its pattern, it is at least the share the check would
            give.
    """

    type: SemanticType
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
    """

    name: str
    type: str
    statistics: Statistics
    matches: tuple[Match, ...] = ()
    values: tuple[Value, ...] = ()

    @property
    def sensitivity(self) -> Sensitivity:
        """The sensitivity of its first match of a sensitive type, or none without one."""
        for match in self.matches:
            if match.type.sensitivity is not Sensitivity.NONE:
                return match.type.sensitivity
        return Sensitivity.NONE


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
            ProfileError: The file cannot be read, is no YAML, holds no fields, is of another
                format, or a field is missing, unknown or of the wrong type.
        """
        try:
            return read_document(path, _ADAPTER, FORMAT)
        except DocumentError as error:
            raise ProfileError(str(error)) from error

    def write(self, path: Path) -> None:
        """Writes the profile to `path`, whole or not at all.

        Args:
            path: The file of the profile.

        Raises:
            ProfileError: The file cannot be written.
        """
        try:
            write_document(path, _ADAPTER, FORMAT, self)
        except DocumentError as error:
            raise ProfileError(str(error)) from error


_ADAPTER: Final = TypeAdapter(Profile)
