"""Overrides: what is given by hand of a profile, and taken as given where it is laid over it.

The overrides of a project are a document of their own, `overrides.yml` in the directory of the
project, the same for all its environments: what the database holds, concepts of the glossary, the
reading of the name of a table or column, the harmonized name of a table or column, the description
of a table or a column, the sensitivity of a column the detectors miss - or find where it is none,
which gives back no values `scan` took out -, and the sentinels of a column, in place of those of
the tool. Concepts are named by their words, tables and columns by their original names, as keys, so
that a person writes no more than what is given.

Every stage takes as given what they give of its work. `scan` takes the sentinels of the columns,
which it counts the table with, and their sensitivity: it lays the overrides over each table it
counts, before the module `disclosure` decides what of its values the profile holds, so that the
profile holds no values of a column marked sensitive. The stages that read the profile - `report`,
and `describe`, which takes the concepts as well - lay them over it whole, so that a mark given
after a scan withholds the values there without a scan again; the sentinels a column was counted
with, they leave as they are. A column has the marks the overrides give it and no others: a mark
taken out gives back no values until `scan` counts the column again, and sentinels changed count
only once it does. A concept given comes before those proposed: it takes the place of the one of its
word, keeping of it only the abbreviations it was proposed with beside those given, and the terms it
is written as - its abbreviations, and its word where it is one term - are taken from the
abbreviations of the others, a concept they take all of dropped, so that a term given is of no
concept but those given, unless it is the word of another, a term of it whatever is given, of which
the reading of its name tells which it stands for, and a term proposed as one more abbreviation of a
concept given is one of it. A reading given comes before the one read; it is laid over by the stages
that read the profile alone, not by `scan`, so that the profile never holds it as read, and it
counts once `describe` has split the name, as a reading agrees with the terms of its name. A name
given comes before the one composed from the reading, so that it resolves a collision of harmonized
names, and a description given before the one proposed; both are laid over by the stages that read
the profile alone, as a reading is, and a column of a description given is not described by the
language model. The descriptions of the database and of a table are laid over the same way, and
shown to the language model with what it is asked of.

An override that names what is not profiled is refused, naming it: `scan` refuses a table it does
not select before it counts anything, and, once it has counted the table, a column the table does
not have and the sentinels given of a column whose values the database writes as no text, which has
none; it does not check the concepts, readings and names, which it does not use. A stage that reads
the profile refuses a table or a column the profile does not have, a reading of a name that is not
one of its terms, as the vocabulary splits it - of another number of words, or a word of no concept
of the term at its place -, and a name given other than in snake_case. An abbreviation given that no
name of the profile has is no mistake, as the overrides are the same for all environments of a
project, whose tables differ: a stage that reads the profile warns of it, once, so that one written
in another case than the terms of the names, which are in lower case, is seen.
"""

import logging
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from data_profiler.detect import Sensitivity
from data_profiler.disclosure import disclose
from data_profiler.documents import DocumentError, Version, read_document
from data_profiler.glossary import (
    Glossary,
    Vocabulary,
    agrees,
    occurrences,
    snake_case,
    written_as,
)
from data_profiler.profile import Concept, Profile, Table

_logger = logging.getLogger(__name__)

# The version of the format of the overrides, raised as `documents` says.
_FORMAT: Final = Version(7, 0)


class OverridesError(Exception):
    """Overrides that cannot be read, or name what the profile they are laid over does not have."""


@dataclass(frozen=True)
class ColumnOverride:
    """What is given by hand of a column.

    Attributes:
        sensitivity: The sensitivity of the column, or None where it is not given.
        sentinels: The values that stand for no value in the column, in place of those of the
            tool, none where empty; None where they are not given.
        reading: The word of the concept each term of its name stands for, in their order, or
            None where it is not given.
        name: Its harmonized name, in snake_case, in place of the one composed from its reading,
            or None where it is not given.
        description: What it holds, in place of the description proposed, or None where it is
            not given.
    """

    sensitivity: Sensitivity | None = None
    sentinels: tuple[str, ...] | None = None
    reading: tuple[str, ...] | None = None
    name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class TableOverride:
    """What is given by hand of a table and its columns.

    Attributes:
        columns: What is given of each column, by its original name.
        reading: The word of the concept each term of the name of the table stands for, in their
            order, or None where it is not given.
        name: The harmonized name of the table, in snake_case, in place of the one composed from
            its reading, or None where it is not given.
        description: What the table holds, or None where it is not given.
    """

    columns: Mapping[str, ColumnOverride] = field(default_factory=dict)
    reading: tuple[str, ...] | None = None
    name: str | None = None
    description: str | None = None

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

    def described_laid_over(
        self, table: Table, vocabulary: Vocabulary, glossary: Glossary
    ) -> Table:
        """`table`, its name and the names of its columns read and named as given, and described so.

        Args:
            table: The table.
            vocabulary: The vocabulary the names are split by, as `describe` splits them.
            glossary: The glossary whose concepts the readings name.

        Returns:
            The table, each reading given in place of the one read, each name given as its
            `name_given`, each description given of a column in place of the one proposed, and the
            description given of the table in place of what it holds.

        Raises:
            OverridesError: A column is named that the table does not have, a reading is given that
                is no reading of the terms of its name, or a name is given that is not in
                snake_case, as `glossary.snake_case` writes it: `address_2`, not `address2`.
        """
        self._refuse_missing(table)
        given = [(table.name, self.reading, self.name)]
        given += [(name, column.reading, column.name) for name, column in self.columns.items()]
        unread = [
            name
            for name, reading, _ in given
            if reading is not None and not agrees(glossary.terms(name, vocabulary), reading)
        ]
        if unread:
            raise OverridesError(
                f"the overrides give readings of names of {table.name} that read no concept of a"
                f" term at its place, or not one of each: {', '.join(unread)}"
            )
        refused = [
            name for name, _, named in given if named is not None and snake_case(named) != named
        ]
        if refused:
            raise OverridesError(
                f"the overrides give names of {table.name} other than in snake_case: "
                + ", ".join(refused)
            )
        columns = []
        for column in table.columns:
            override = self.columns.get(column.name, ColumnOverride())
            columns.append(
                replace(
                    column,
                    reading=column.reading if override.reading is None else override.reading,
                    name_given=override.name,
                    description=(
                        column.description if override.description is None else override.description
                    ),
                )
            )
        reading = table.reading if self.reading is None else self.reading
        description = table.description if self.description is None else self.description
        return replace(
            table,
            columns=tuple(columns),
            reading=reading,
            name_given=self.name,
            description=description,
        )

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
    """What is given by hand of a profile: concepts, readings, descriptions, sensitivity, sentinels.

    Attributes:
        description: What the database holds, or None where it is not given.
        glossary: The concepts given, by their words.
        tables: What is given of each table, by its original name.
    """

    description: str | None = None
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
            OverridesError: The file cannot be read, is no YAML, names no version of a format, is
                of another major version or of a newer minor version, or a field is missing,
                unknown or of the wrong type.
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

    def warn_unused(self, profile: Profile) -> None:
        """Warns of the abbreviations given that no name of `profile` has, naming them.

        A word given that no name has is not warned of, as a concept is given by its word whatever
        the names are.

        Args:
            profile: The profile the overrides are laid over.
        """
        abbreviations = {t for concept in self.glossary.values() for t in concept.abbreviations}
        # Split by the concepts given, as an abbreviation given is no longer split.
        unused = sorted(abbreviations - set(occurrences(self._with_concepts(profile))))
        if unused:
            _logger.warning(
                "The overrides give abbreviations, in lower case as terms are, that no name of the"
                " profile has: %s",
                ", ".join(unused),
            )

    def laid_over(self, profile: Profile) -> Profile:
        """`profile` with what the overrides give taken as given.

        Args:
            profile: The profile.

        Returns:
            The profile, the concepts of the overrides in its glossary before its own, the
            readings they give of the names of its tables and columns in place of those read, the
            names they give as their `name_given`, the descriptions they give of its columns in
            place of those proposed, and of it and its tables in place of what they hold, its
            columns marked with the sensitivity they
            give, and only so, and without the values of those marked sensitive.

        Raises:
            OverridesError: The overrides name a table or column the profile does not have, or
                give a reading of a name that is no reading of its terms, as the vocabulary of the
                profile splits it: of another number of words, or a word of no concept of the term
                at its place, or a name other than in snake_case.
        """
        profile = self._with_concepts(profile)
        vocabulary = Vocabulary.of(profile)
        glossary = Glossary(profile.glossary)
        given = self.selected([table.name for table in profile.tables])
        tables = (
            disclose(
                given[table.name].described_laid_over(
                    given[table.name].laid_over(table), vocabulary, glossary
                ),
                profile.types,
            )
            for table in profile.tables
        )
        description = profile.description if self.description is None else self.description
        return replace(profile, tables=tuple(tables), description=description)

    def _with_concepts(self, profile: Profile) -> Profile:
        """`profile`, the concepts given in its glossary before its own."""
        return replace(profile, glossary=_laid_over(self.glossary, profile.glossary))


def _laid_over(given: Mapping[str, Concept], proposed: Mapping[str, Concept]) -> dict[str, Concept]:
    """The concepts `given`, with those `proposed` without the terms the given are written as.

    A concept proposed of the word of one given adds to it the abbreviations it has left; one of
    another word is dropped once all its abbreviations are taken, and keeps its word, which is
    taken from none: one without abbreviations, written as its word alone, is kept.
    """
    taken = {term for word, concept in given.items() for term in written_as(word, concept)}
    concepts = dict(given)
    for word, concept in proposed.items():
        left = tuple(term for term in concept.abbreviations if term not in taken)
        if word in given:
            concepts[word] = replace(given[word], abbreviations=(*given[word].abbreviations, *left))
        elif left or not concept.abbreviations:
            concepts[word] = replace(concept, abbreviations=left)
    return concepts


_ADAPTER: Final = TypeAdapter(Overrides)
