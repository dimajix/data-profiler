"""Overrides: what is given by hand of a profile, and taken as given where it is laid over it.

The overrides of a project are a document of their own, `overrides.yml` in the directory of the
project, the same for all its environments: concepts of the glossary, the sensitivity of a column
the detectors miss - or find where it is none, which gives back no values `scan` took out -, and the
sentinels of a column, in place of those of the tool. Concepts are named by their words, tables and
columns by their original names, as keys, so that a person writes no more than what is given.

Every stage takes as given what they give of its work. `scan` takes the sentinels of the columns,
which it counts the table with, and their sensitivity: it lays the overrides over each table it
counts, before the module `disclosure` decides what of its values the profile holds, so that the
profile holds no values of a column marked sensitive. The stages that read the profile - `report`,
and `describe`, which takes the concepts as well - lay them over it whole, so that a
mark given after a scan withholds the values there without a scan again; the sentinels a column was
counted with, they leave as they are. A column has the marks the overrides give it and no others: a
mark taken out gives back no values until `scan` counts the column again, and sentinels changed
count only once it does. A concept given comes before those proposed: it takes the place of the
one of its word, and its abbreviations are taken from the others, a concept left without any
dropped, so that a term given is of no concept but those given.

An override that names what is not profiled is refused, naming it: `scan` refuses a table it does
not select before it counts anything, and, once it has counted the table, a column the table does
not have and the sentinels given of a column whose values the database writes as no text, which
has none; it does not check the concepts, which it does not use. A stage that reads the profile
refuses a table or a column the profile does not have, and an abbreviation no name of it has.
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
from data_profiler.profile import Concept, Profile, Table

# The version of the format of the overrides, raised as `profile.FORMAT` is.
_FORMAT: Final = 3


class OverridesError(Exception):
    """Overrides that cannot be read, or name what the profile they are laid over does not have."""


@dataclass(frozen=True)
class ColumnOverride:
    """What is given by hand of a column.

    Attributes:
        sensitivity: The sensitivity of the column, or None where it is not given.
        sentinels: The values that stand for no value in the column, in place of those of the
            tool, none where empty; None where they are not given.
    """

    sensitivity: Sensitivity | None = None
    sentinels: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TableOverride:
    """What is given by hand of the columns of a table.

    Attributes:
        columns: What is given of each column, by its original name.
    """

    columns: Mapping[str, ColumnOverride] = field(default_factory=dict)

    @property
    def sentinels(self) -> dict[str, tuple[str, ...]]:
        """The sentinels given of the columns, by their names, of those they are given of."""
        return {
            name: column.sentinels
            for name, column in self.columns.items()
            if column.sentinels is not None
        }

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
        self._refuse_missing(table)
        columns = (replace(column, marked=self._marked(column.name)) for column in table.columns)
        return replace(table, columns=tuple(columns))

    def agrees_with(self, table: Table) -> bool:
        """Whether `table` agrees with what is given: marked, and counted with the sentinels given.

        Args:
            table: The table.

        Returns:
            True where `laid_over` would leave the table as it is and each column was counted with
            the sentinels given of it; False where it would mark its columns otherwise, a column
            was counted with others, or the table lacks a column that is named.
        """
        return (
            not self._missing(table)
            and self.laid_over(table) == table
            and not self._counted_otherwise(table)
        )

    def refuse_uncounted(self, table: Table) -> None:
        """Refuses what is given of `table` that it was not counted with, once it is counted.

        Right after `statistics.count`, a column is counted otherwise than given only where its
        values are no text, which `count` counts without sentinels, whatever is given.

        Args:
            table: The table, as `statistics.count` counted it.

        Raises:
            OverridesError: A column is named that the table does not have, or sentinels are
                given of a column of no text.
        """
        self._refuse_missing(table)
        refused = self._counted_otherwise(table)
        if refused:
            raise OverridesError(
                f"the overrides give sentinels of columns of {table.name} whose values are no"
                f" text: {', '.join(refused)}"
            )

    def _missing(self, table: Table) -> list[str]:
        """The columns given that `table` does not have, sorted by their names."""
        return sorted(set(self.columns) - {column.name for column in table.columns})

    def _refuse_missing(self, table: Table) -> None:
        """Refuses what is given of the columns `table` does not have, naming them."""
        missing = self._missing(table)
        if missing:
            raise OverridesError(
                f"the overrides name columns of {table.name} it does not have: {', '.join(missing)}"
            )

    def _counted_otherwise(self, table: Table) -> list[str]:
        """The columns of `table` counted with other sentinels than given, sorted by their names."""
        given = self.sentinels
        return sorted(c.name for c in table.columns if c.sentinels != given.get(c.name))

    def _marked(self, name: str) -> Sensitivity | None:
        """The sensitivity given of the column `name`, or None where none is."""
        given = self.columns.get(name)
        return None if given is None else given.sensitivity


@dataclass(frozen=True)
class Overrides:
    """What is given by hand of a profile: concepts, sensitivity and sentinels of columns.

    Attributes:
        glossary: The concepts given, by their words.
        tables: What is given of each table, by its original name.
    """

    glossary: Mapping[str, Concept] = field(default_factory=dict)
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
            The profile, the concepts of the overrides in its glossary before its own, its columns
            marked with the sensitivity they give, and only so, and without the values of those
            marked sensitive.

        Raises:
            OverridesError: The overrides give an abbreviation that no name of the profile has,
                or name a table or column the profile does not have.
        """
        taken = {term for concept in self.glossary.values() for term in concept.abbreviations}
        concepts = _laid_over(self.glossary, taken, profile.glossary)
        # Split by the concepts given, as an abbreviation given is no longer split.
        unknown = sorted(taken - set(occurrences(replace(profile, glossary=concepts))))
        if unknown:
            raise OverridesError(
                "the overrides give abbreviations, in lower case as terms are, that no name of"
                " the profile has: " + ", ".join(unknown)
            )
        given = self.selected([table.name for table in profile.tables])
        tables = (
            disclose(given[table.name].laid_over(table), profile.types) for table in profile.tables
        )
        return replace(profile, tables=tuple(tables), glossary=concepts)


def _laid_over(
    given: Mapping[str, Concept], taken: Collection[str], proposed: Mapping[str, Concept]
) -> dict[str, Concept]:
    """The concepts `given`, whose abbreviations are `taken`, with those `proposed` without them."""
    kept = {}
    for word, concept in proposed.items():
        left = tuple(term for term in concept.abbreviations if term not in taken)
        if word not in given and left:
            kept[word] = replace(concept, abbreviations=left)
    return {**given, **kept}


_ADAPTER: Final = TypeAdapter(Overrides)
