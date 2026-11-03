"""Overrides: what is given by hand of a profile, and taken as given where it is laid over it.

The overrides of a project are a document of their own, `overrides.yml` in the directory of the
project, the same for all its environments: the word of a term of the glossary, and the sensitivity
of a column the detectors miss - or find where it is none, which gives back no values `scan` took
out. Tables, columns and terms are named by their original names, as keys, so that a person writes
no more than what is given.

Every stage takes as given what they give of its work. `scan` takes the sensitivity of the columns:
it lays the overrides over each table it counts, before the module `disclosure` decides what of its
values the profile holds, so that the profile holds no values of a column marked sensitive. The
stages that read the profile - `report`, and `describe`, which takes the words of terms as well -
lay them over it whole, so that a mark given after a scan withholds the values there without a scan
again. A column has the marks the overrides give it and no others: a mark taken out gives back no
values until `scan` counts the column again.

An override that names what is not profiled is refused, naming it: `scan` refuses a table it does
not select before it counts anything, and a column its table does not have once it has counted the
table; it does not check the terms, which it does not use. A stage that reads the profile refuses
a table, a column or a term the profile does not have.
"""

from collections.abc import Collection, Mapping
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

    def laid_over(self, table: Table) -> Table:
        """`table`, each of its columns marked with the sensitivity given of it, and only so.

        Args:
            table: The table.

        Returns:
            The table, its columns marked as given, and only so; their values as they are, for
            the module `disclosure` to decide on.

        Raises:
            OverridesError: A column is named that the table does not have.
        """
        missing = self._missing(table)
        if missing:
            raise OverridesError(
                f"the overrides name columns of {table.name} it does not have: {', '.join(missing)}"
            )
        columns = (replace(column, marked=self._marked(column.name)) for column in table.columns)
        return replace(table, columns=tuple(columns))

    def is_laid_over(self, table: Table) -> bool:
        """Whether the columns of `table` are marked as given, and no others are.

        Args:
            table: The table.

        Returns:
            True where `laid_over` would leave the table as it is; False where it would mark its
            columns otherwise, or the table lacks a column that is named.
        """
        return not self._missing(table) and self.laid_over(table) == table

    def _missing(self, table: Table) -> list[str]:
        """The columns given that `table` does not have, sorted by their names."""
        return sorted(set(self.columns) - {column.name for column in table.columns})

    def _marked(self, name: str) -> Sensitivity | None:
        """The sensitivity given of the column `name`, or None where none is."""
        given = self.columns.get(name)
        return None if given is None else given.sensitivity


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

    def selected(self, names: Collection[str]) -> dict[str, TableOverride]:
        """What is given of each table of `names`, an override of nothing where none is given.

        Args:
            names: The names of the tables of a profile, or of those a scan selected.

        Returns:
            What is given of each table, by its name.

        Raises:
            OverridesError: A table is named that `names` does not name.
        """
        missing = sorted(set(self.tables) - set(names))
        if missing:
            raise OverridesError(
                f"the overrides name tables that are not profiled: {', '.join(missing)}"
            )
        return {name: self.tables.get(name, TableOverride()) for name in names}

    def laid_over(self, profile: Profile) -> Profile:
        """`profile` with what the overrides give taken as given.

        Args:
            profile: The profile.

        Returns:
            The profile, the words of the overrides in its glossary, its columns marked with the
            sensitivity they give, and only so, and without the values of those marked sensitive.

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
        given = self.selected([table.name for table in profile.tables])
        tables = (
            disclose(given[table.name].laid_over(table), profile.types) for table in profile.tables
        )
        return replace(
            profile, tables=tuple(tables), glossary={**profile.glossary, **self.glossary}
        )


_ADAPTER: Final = TypeAdapter(Overrides)
