"""Overrides: what is given by hand of a profile, and taken as given where it is laid over it.

The overrides of a project are a document of their own, `overrides.yml` in the directory of the
project, the same for all its environments: the word of a term of the glossary, and the sensitivity
of a column the detectors miss - or find where it is none, which gives back no values `scan` took
out. Tables, columns and terms are named by
their original names, as keys, so that a person writes no more than what is given. They are laid
over a profile by the stages that read one, never by `scan`; a column marked sensitive loses its
values where they are laid over, by the module `disclosure`, so that a mark needs no scan again.
An override that names what the profile does not have is refused, naming it.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from data_profiler.detect import Sensitivity
from data_profiler.disclosure import disclose
from data_profiler.documents import DocumentError, read_document
from data_profiler.glossary import occurrences
from data_profiler.profile import Profile, Table

# The version of the format of the overrides, raised as `profile.FORMAT` is.
_FORMAT: Final = 1


class OverridesError(Exception):
    """Overrides that cannot be read, or name what the profile they are laid over does not have."""


@dataclass(frozen=True)
class ColumnOverride:
    """What is given by hand of a column.

    Attributes:
        sensitivity: The sensitivity of the column, or None where it is not given.
    """

    sensitivity: Sensitivity | None = None


@dataclass(frozen=True)
class TableOverride:
    """What is given by hand of the columns of a table.

    Attributes:
        columns: What is given of each column, by its original name.
    """

    columns: Mapping[str, ColumnOverride] = field(default_factory=dict)


@dataclass(frozen=True)
class Overrides:
    """What is given by hand of a profile: the words of terms, the sensitivity of columns.

    Attributes:
        glossary: The word of each term given, by the term, in lower case.
        tables: What is given of each table, by its original name.
    """

    glossary: Mapping[str, str] = field(default_factory=dict)
    tables: Mapping[str, TableOverride] = field(default_factory=dict)

    @classmethod
    def read(cls, path: Path) -> "Overrides":
        """The overrides in `path`; none where there is no such file.

        Args:
            path: The file of the overrides.

        Returns:
            The overrides.

        Raises:
            OverridesError: The file cannot be read, is no YAML, is of another format, or a
                field is missing, unknown or of the wrong type.
        """
        if not path.exists():
            return cls()
        try:
            return read_document(path, _ADAPTER, _FORMAT)
        except DocumentError as error:
            raise OverridesError(str(error)) from error

    def laid_over(self, profile: Profile) -> Profile:
        """`profile` with what the overrides give taken as given.

        Args:
            profile: The profile.

        Returns:
            The profile, the words of the overrides in its glossary, its columns with the
            sensitivity they give, and without the values of those it marks sensitive.

        Raises:
            OverridesError: The overrides give the word of a term that no name of the profile
                has, or name a table or column the profile does not have.
        """
        unknown = sorted(set(self.glossary) - set(occurrences(profile)))
        if unknown:
            raise OverridesError(
                "the overrides give words of terms, in lower case as terms are, that no name of"
                " the profile has: " + ", ".join(unknown)
            )
        tables = {table.name: table for table in profile.tables}
        missing = sorted(set(self.tables) - set(tables))
        if missing:
            raise OverridesError(
                f"the overrides name tables the profile does not have: {', '.join(missing)}"
            )
        for name, given in self.tables.items():
            tables[name] = _laid_over(given, tables[name])
        return replace(
            profile,
            tables=tuple(tables[table.name] for table in profile.tables),
            glossary={**profile.glossary, **self.glossary},
        )


_ADAPTER: Final = TypeAdapter(Overrides)


def _laid_over(given: TableOverride, table: Table) -> Table:
    """`table` with what `given` gives of its columns, and its values disclosed again."""
    columns = {column.name: column for column in table.columns}
    missing = sorted(set(given.columns) - set(columns))
    if missing:
        raise OverridesError(
            f"the overrides name columns of {table.name} it does not have: {', '.join(missing)}"
        )
    for name, column in given.columns.items():
        if column.sensitivity is not None:
            columns[name] = replace(columns[name], marked=column.sensitivity)
    return disclose(replace(table, columns=tuple(columns.values())))
