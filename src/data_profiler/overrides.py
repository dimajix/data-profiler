"""Overrides: what is given by hand of a profile, kept in files and taken as given laid over it.

The overrides of a project are documents of their own, `overrides.yml` and the files of the
directory `overrides/` of the project, the same for all its environments, read merged by
`Overrides.read`: what is given of the database, concepts of the glossary, and what is given of each
table and its columns, as the classes below hold it. What each override gives, which stage takes it
and when it counts, and what is refused or warned of, is said in `docs/PROJECT.md`; here is how the
stages take it.

`scan` takes what is given of each table it selects, a `TableOverride`, by `Overrides.selected`:
`agrees_with` tells whether a table a run resumed counted is to be counted again; its `sentinels` go
to the counting of the table, after which `refuse_uncounted` refuses a column the table does not
have, a primary key that cannot be one, and sentinels the table was not counted with; its
`list_separator`, in place of that of the project, to the columns of lists, `primary_key` to the
keys, `determining_none` to the column dependencies, and `discriminator` to the entities; and
`TableOverride.laid_over` marks its columns and drops the dependencies of a column determining none,
refusing a primary key or a discriminator that cannot be one, before the module `disclosure` decides
what of its values the profile holds, so that the profile holds no values of a column marked
sensitive. `relate` takes the references given, by `Overrides.references`, refused before it queries
anything. The stages that read the profile - `describe` and `report` - lay the overrides over it
whole, by `Overrides.laid_over`: the concepts given before those proposed, the references given
refused as `relate` refuses them, then each table laid over as `scan` lays it, then read, named and
described as given, by `TableOverride.described_laid_over`, then disclosed again, so that a mark
given after a scan withholds the values without a scan again; `Overrides.warn_unused` warns of what
is given that the profile does not take. `describe` shows the language model the description given
of the database, `Overrides.description`, and `report` tells the concepts given apart from those
proposed by `Overrides.glossary`. `adopt` writes to the overrides what a person takes over of the
concepts proposed: `Overrides.adoptable` says what a concept proposed adds, and `Overrides.amend`
sets it in the file it belongs to.
"""

import logging
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final, Literal

from data_profiler.detect import Sensitivity
from data_profiler.disclosure import disclose
from data_profiler.documents import DocumentError, Format, Version
from data_profiler.glossary import (
    Glossary,
    Vocabulary,
    agrees,
    occurrences,
    snake_case,
    terms,
    written_as,
)
from data_profiler.profile import (
    Concept,
    Discriminator,
    ListSeparator,
    PrimaryKey,
    Profile,
    Table,
)

_logger = logging.getLogger(__name__)


class OverridesError(Exception):
    """Overrides that cannot be read, or name what the profile they are laid over does not have."""


@dataclass(frozen=True)
class ReferenceOverride:
    """The key of one column a column refers to, given by hand.

    Attributes:
        table: The name of the table referred to, of another or of the table of the column.
        column: The name of its column of the key referred to.
    """

    table: str
    column: str


# What the overrides give of the reference of a column: the key it refers to, or False for none,
# whatever is found; None where they give nothing of it.
type GivenReference = ReferenceOverride | Literal[False] | None

# The references the overrides give of the columns of a table, by their names: the key, or False.
type GivenReferences = Mapping[str, ReferenceOverride | Literal[False]]


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
        reference: The key it refers to, or False where it refers to none, whatever is found;
            None where it is not given.
        determines: False where it determines no other column, whatever is found; None where it
            is not given.
    """

    sensitivity: Sensitivity | None = None
    sentinels: tuple[str, ...] | None = None
    reading: tuple[str, ...] | None = None
    name: str | None = None
    description: str | None = None
    reference: GivenReference = None
    determines: Literal[False] | None = None


@dataclass(frozen=True)
class EntityOverride:
    """What is given by hand of an entity of a table: its values, and what it holds.

    Attributes:
        values: Values of the discriminator its rows hold, as text, one at least; the others it is
            found of join them.
        description: What it holds, or None where it is not given.
    """

    values: tuple[str, ...]
    description: str | None = None


@dataclass(frozen=True)
class DiscriminatorOverride:
    """The discriminator of a table given by hand, and its entities by their harmonized names.

    Attributes:
        column: The name of the column whose values tell the entities apart, an enumeration of no
            sensitivity, or a column of lists whose values are one, which tell them apart.
        entities: What is given of its entities, by their harmonized names, in snake_case; the
            values given of none join them, or are of entities found as `scan` finds them.
    """

    column: str
    entities: Mapping[str, EntityOverride] = field(default_factory=dict)

    @property
    def values(self) -> tuple[tuple[str, ...], ...]:
        """The values of each of its entities, in their order, as a discriminator records them."""
        return tuple(entity.values for entity in self.entities.values())


# What the overrides give of the discriminator of a table: the discriminator, or False for none,
# whatever is found; None where they give nothing of it.
type GivenDiscriminator = DiscriminatorOverride | Literal[False] | None


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
        discriminator: The discriminator of its entities, or False where it has none, whatever is
            found; None where it is not given.
        primary_key: The columns of its primary key, in place of the one chosen among its keys,
            one at least and each once, or None where it is not given.
        list_separator: The separator of the values of the lists in its texts, in place of that of
            the project - one character, no letter, digit, `-`, `+` or `_` -, or None where it is
            not given.
    """

    columns: Mapping[str, ColumnOverride] = field(default_factory=dict)
    reading: tuple[str, ...] | None = None
    name: str | None = None
    description: str | None = None
    discriminator: GivenDiscriminator = None
    primary_key: tuple[str, ...] | None = None
    list_separator: ListSeparator | None = None

    @property
    def sentinels(self) -> dict[str, tuple[str, ...]]:
        """The sentinels given of the columns, by their names, of those they are given of."""
        return {
            name: column.sentinels
            for name, column in self.columns.items()
            if column.sentinels is not None
        }

    @property
    def determining_none(self) -> frozenset[str]:
        """The columns given as determining no other column, by their names."""
        return frozenset(
            name for name, column in self.columns.items() if column.determines is False
        )

    @property
    def _discriminator(self) -> DiscriminatorOverride | None:
        """The discriminator given, or None where none is, or False."""
        return self.discriminator if isinstance(self.discriminator, DiscriminatorOverride) else None

    def laid_over(self, table: Table) -> Table:
        """`table`, its columns marked as given, without the dependencies of those given as none.

        Args:
            table: The table.

        Returns:
            The table, its columns marked with the sensitivity given of each, and only so, their
            values as they are, for the module `disclosure` to decide on; without the column
            dependencies of which a determinant is given as determining no other column.

        Raises:
            OverridesError: A column is named that the table does not have, or a primary key is
                given of no columns or of a column twice, or a discriminator of a column they mark
                of a sensitivity, or of entities of no values, or of a value twice.
        """
        self._refuse_missing(table)
        self._refuse_primary_key(table)
        columns = (replace(column, marked=self._marked(column.name)) for column in table.columns)
        none = self.determining_none
        dependencies = (
            found for found in table.column_dependencies if none.isdisjoint(found.determinants)
        )
        marked = replace(table, columns=tuple(columns), column_dependencies=tuple(dependencies))
        self._refuse_discriminator(marked)
        return marked

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
            `name_given`, each description given of a column in place of the one proposed, the
            description given of the table in place of what it holds, and the name and the
            description given of each entity of its discriminator, where it is the one given.

        Raises:
            OverridesError: A column is named that the table does not have, a reading is given that
                is no reading of the terms of its name, or a name is given that is not in
                snake_case, as `glossary.snake_case` writes it: `first_name`, not `FirstName`.
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
        entities = [] if self._discriminator is None else list(self._discriminator.entities)
        refused = [
            name for name, _, named in given if named is not None and snake_case(named) != named
        ]
        refused += [name for name in entities if snake_case(name) != name]
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
            discriminator=self._named(table.discriminator),
        )

    def agrees_with(self, table: Table) -> bool:
        """Whether `table` agrees with what is given: marked, counted, determined and discriminated.

        The separator of lists is judged by `scan`, by `lists.is_listed_with`, as it is that of the
        project where none is given, which an override of a table does not know.

        Args:
            table: The table.

        Returns: True where `laid_over` would leave the table as it is, each column was counted with
            the sentinels given of it, the table has the primary key given, or one chosen where none
            is given, and was discriminated as given: its discriminator counted with the values
            given of its entities, none where False is given, and one found or none where nothing is
            given; False where it would mark its columns otherwise, or the table holds a column
            dependency of a column given as determining none, a column was counted with others, the
            table has another primary key, was discriminated otherwise, or lacks a
            column that is named.

        Raises:
            OverridesError: The primary key or the discriminator given is refused, as
                `laid_over` says, where the table has the primary key and the discriminator given.
        """
        return (
            not self._missing(table)
            and _as_given(self.discriminator, table.discriminator)
            and _keyed_as_given(self.primary_key, table.primary_key)
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
            OverridesError: A column is named that the table does not have, a primary key is given
                of no columns or of a column twice, or sentinels are given of a column of no text.
        """
        self._refuse_missing(table)
        self._refuse_primary_key(table)
        refused = self._counted_otherwise(table)
        if refused:
            raise OverridesError(
                f"the overrides give sentinels of columns of {table.name} whose values are no"
                f" text: {', '.join(refused)}"
            )

    def references(self, table: Table, profile: Profile) -> GivenReferences:
        """The references given of the columns of `table`, of `profile`, of those given.

        Args:
            table: The table, of the profile.
            profile: The profile, whose tables the references refer to.

        Returns:
            The reference given of each column, the key or False, by its name.

        Raises:
            OverridesError: A column is named that the table does not have, or a reference is
                given of a column to itself, to a table the profile does not have, or to a column
                the table referred to does not have.
        """
        self._refuse_missing(table)
        given = {
            name: column.reference
            for name, column in self.columns.items()
            if column.reference is not None
        }
        for name, reference in given.items():
            if reference is False:
                continue
            where = f"the overrides give {table.name}.{name} as a reference to"
            if (reference.table, reference.column) == (table.name, name):
                raise OverridesError(f"{where} itself")
            if reference.table not in {found.name for found in profile.tables}:
                raise OverridesError(f"{where} {reference.table}, which is not profiled")
            referred = profile.table(reference.table)
            if reference.column not in {column.name for column in referred.columns}:
                raise OverridesError(
                    f"{where} {referred.name}.{reference.column}, which {referred.name} does not"
                    " have"
                )
        return given

    def _missing(self, table: Table) -> list[str]:
        """The columns named, of the primary key and the discriminator too, `table` lacks."""
        named = set(self.columns) | set(self.primary_key or ())
        if self._discriminator is not None:
            named.add(self._discriminator.column)
        return sorted(named - {column.name for column in table.columns})

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

    def _refuse_primary_key(self, table: Table) -> None:
        """Refuses the primary key given of `table` where it is of no columns or of one twice.

        Raises:
            OverridesError: The primary key is given of no columns, or of a column twice.
        """
        given = self.primary_key
        if given is None:
            return
        if not given:
            raise OverridesError(f"the overrides give a primary key of {table.name} of no columns")
        twice = sorted({name for name in given if given.count(name) > 1})
        if twice:
            raise OverridesError(
                f"the overrides give a primary key of {table.name} of columns twice: "
                + ", ".join(twice)
            )

    def _refuse_discriminator(self, table: Table) -> None:
        """Refuses the discriminator given of `table`, its columns marked, where it cannot be one.

        What it holds is not judged here, nor a sensitivity its matches find: the values given of
        an environment that does not hold them, `scan` leaves out, warning of them, as the
        overrides are of all environments.

        Raises:
            OverridesError: The overrides mark its column of a sensitivity, or an entity is given
                of no values, or a value is given of two entities.
        """
        given = self._discriminator
        if given is None:
            return
        column = table.column(given.column)
        where = f"the overrides give the discriminator of {table.name} as {column.name}"
        if column.marked is not None and column.sensitive:
            raise OverridesError(f"{where}, a column they mark of a sensitivity")
        empty = [name for name, entity in given.entities.items() if not entity.values]
        if empty:
            raise OverridesError(f"{where}, and entities of no values: {', '.join(empty)}")
        values = [value for values in given.values for value in values]
        if len(values) != len(set(values)):
            raise OverridesError(f"{where}, and a value of it twice among its entities")

    def _named(self, discriminator: Discriminator | None) -> Discriminator | None:
        """`discriminator`, its entities named and described as given, where it was counted so.

        An entity is named after the entity given whose values it holds.
        """
        given = self._discriminator
        if given is None or discriminator is None or not _as_given(given, discriminator):
            return discriminator
        names = {value: name for name, entity in given.entities.items() for value in entity.values}
        entities = []
        for entity in discriminator.entities:
            name = next((names[value] for value in entity.values if value in names), None)
            entities.append(
                entity
                if name is None
                else replace(entity, name_given=name, description=given.entities[name].description)
            )
        return replace(discriminator, entities=tuple(entities))

    def _marked(self, name: str) -> Sensitivity | None:
        """The sensitivity given of the column `name`, or None where none is."""
        given = self.columns.get(name)
        return None if given is None else given.sensitivity


@dataclass(frozen=True)
class Overrides:
    """What is given by hand of a profile: concepts, names, descriptions, columns, discriminators.

    Attributes:
        description: What the database holds, or None where it is not given.
        glossary: The concepts given, by their words.
        tables: What is given of each table, by its original name.
    """

    description: str | None = None
    glossary: Mapping[str, Concept] = field(default_factory=dict)
    tables: Mapping[str, TableOverride] = field(default_factory=dict)

    @classmethod
    def read(cls, paths: Sequence[Path]) -> "Overrides":
        """The overrides in the files `paths`, merged; none where there are no files.

        Args:
            paths: The files of the overrides.

        Returns:
            The overrides.

        Raises:
            OverridesError: A file cannot be read, is no YAML, names no version of a format, is of
                another major version or of a newer minor version, or a field is missing, unknown
                or of the wrong type; or a field is given in two files.
        """
        try:
            return FORMAT.read_merged(paths)
        except DocumentError as error:
            raise OverridesError(str(error)) from error

    @classmethod
    def amend(
        cls, paths: Sequence[Path], field: Sequence[str], value: object, otherwise: Path
    ) -> None:
        """Sets a field of the overrides in the files `paths`, as `Format.amend` does.

        Args:
            paths: The files of the overrides.
            field: The keys of the field, from the top of a document on.
            value: Its value.
            otherwise: The file it is set in where no file of `paths` names its entry.

        Raises:
            OverridesError: A file cannot be read or written, is no YAML or of another format, or
                what holds the field cannot hold it.
        """
        try:
            FORMAT.amend(paths, field, value, otherwise)
        except DocumentError as error:
            raise OverridesError(str(error)) from error

    def adoptable(self, word: str, proposed: Concept) -> Concept:
        """What `proposed`, the concept proposed of `word`, adds to those given, empty if nothing.

        What is left of it is what `Overrides.laid_over` leaves of it: a concept dropped there adds
        nothing.

        Args:
            word: The word of the concept proposed.
            proposed: The concept proposed.

        Returns:
            A concept of the abbreviations proposed that it is not written as yet, by the concepts
            given and its word, and of the description proposed where none is given of it; empty,
            equal to `Concept()`, where there is neither.
        """
        laid = _laid_over(self.glossary, {word: proposed}).get(word)
        if laid is None:
            return Concept()
        given = self.glossary.get(word, Concept())
        written = written_as(word, given)
        return Concept(
            tuple(term for term in laid.abbreviations if term not in written),
            proposed.description if given.description is None else None,
        )

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

    def references(self, profile: Profile) -> dict[str, GivenReferences]:
        """The references given of the columns of `profile`, of those they are given of.

        Args:
            profile: The profile whose tables are related.

        Returns:
            The reference given of each column, the key or False, by the names of its table and
            its own; none of a table of none given.

        Raises:
            OverridesError: A table is named that the profile does not have, or a column its table
                does not have, or a reference is given that cannot be one, as
                `TableOverride.references` says.
        """
        given = self.selected([table.name for table in profile.tables])
        references = {
            table.name: given[table.name].references(table, profile) for table in profile.tables
        }
        return {name: found for name, found in references.items() if found}

    def warn_unused(self, profile: Profile) -> None:
        """Warns of what is given that `profile` does not take, naming it.

        An abbreviation given that no name of it has is warned of; a word given that no name has
        is not, as a concept is given by its word whatever the names are. A discriminator given of
        a table that was discriminated otherwise is warned of as well, as it counts, and the names
        of its entities are laid over, only once `scan` counts the table again; and a reference
        given of a column that was related otherwise, as it counts once `relate` relates the
        tables again.

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
        otherwise = [
            table.name
            for table in profile.tables
            if not _as_given(
                self.tables.get(table.name, TableOverride()).discriminator, table.discriminator
            )
        ]
        if otherwise:
            _logger.warning(
                "The overrides give the discriminators of tables otherwise than the profile was"
                " counted with, until scan counts them again: %s",
                ", ".join(otherwise),
            )
        unrelated = [
            f"{table.name}.{column.name}"
            for table in profile.tables
            for column in table.columns
            if not _referred_as_given(self._reference(table.name, column.name), table, column.name)
        ]
        if unrelated:
            _logger.warning(
                "The overrides give the references of columns otherwise than the profile was"
                " related with, until relate relates them again: %s",
                ", ".join(unrelated),
            )

    def laid_over(self, profile: Profile) -> Profile:
        """`profile` with what the overrides give taken as given.

        Args:
            profile: The profile.

        Returns:
            The profile, the concepts of the overrides in its glossary before its own, the
            readings they give of the names of its tables and columns in place of those read, the
            names they give as their `name_given`, the descriptions they give of its columns in
            place of those proposed, and of it and its tables in place of what they hold, the
            names and descriptions they give of the entities of a discriminator as given, its
            columns marked with the sensitivity they give, and only so, and without the values of
            those marked sensitive, and its tables without the column dependencies of a column
            they give as determining none.

        Raises:
            OverridesError: The overrides name a table or column the profile does not have, or
                give a reading of a name that is no reading of its terms, as the vocabulary of the
                profile splits it: of another number of words, or a word of no concept of the term
                at its place, or a name other than in snake_case, or a discriminator that cannot be
                one, as `TableOverride.laid_over` says, or a reference, as
                `TableOverride.references` says.
        """
        profile = self._with_concepts(profile)
        vocabulary = Vocabulary.of(profile)
        glossary = Glossary(profile.glossary)
        given = self.selected([table.name for table in profile.tables])
        # The references are not laid over, which relate takes, but refused as it refuses them.
        for table in profile.tables:
            given[table.name].references(table, profile)
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

    def _reference(self, table: str, column: str) -> GivenReference:
        """The reference given of the column `column` of the table `table`, or None."""
        given = self.tables.get(table, TableOverride()).columns.get(column)
        return None if given is None else given.reference

    def _with_concepts(self, profile: Profile) -> Profile:
        """`profile`, the concepts given in its glossary before its own."""
        return replace(profile, glossary=_laid_over(self.glossary, profile.glossary))


def _keyed_as_given(given: tuple[str, ...] | None, primary: PrimaryKey | None) -> bool:
    """Whether a table of `primary` has the primary key `given`, as `agrees_with` says."""
    if given is None:
        return primary is None or not primary.given
    return primary is not None and primary.given and set(primary.columns) == set(given)


def _referred_as_given(given: GivenReference, table: Table, column: str) -> bool:
    """Whether the column `column` of `table` was related as `given`, as `warn_unused` says.

    It has the reference given, where one is; none and no reference candidates, where False is; and
    none given, where nothing is.
    """
    reference = table.reference(column)
    if given is None:
        return reference is None or not reference.given
    if given is False:
        return reference is None and all(
            found.column != column for found in table.reference_candidates
        )
    return (
        reference is not None
        and reference.given
        and (reference.table, reference.key) == (given.table, given.column)
    )


def _as_given(given: GivenDiscriminator, discriminator: Discriminator | None) -> bool:
    """Whether a table of `discriminator` was discriminated as `given`, as `agrees_with` says."""
    if given is None:
        return discriminator is None or discriminator.given is None
    if given is False:
        return discriminator is None
    return (
        discriminator is not None
        and discriminator.column == given.column
        and discriminator.given == given.values
    )


def _laid_over(given: Mapping[str, Concept], proposed: Mapping[str, Concept]) -> dict[str, Concept]:
    """The concepts `given`, with those `proposed` without the terms the given are written as.

    A concept proposed of the word of one given adds to it the abbreviations it has left; one of
    another word is dropped once its abbreviations are all taken, or its word where it has none.
    Else it keeps its word, which is taken from none. Two words are one where their pieces are, as
    `b_2_b`, which a profile may hold of words written before, and `b2b` are.
    """
    taken = {term for word, concept in given.items() for term in written_as(word, concept)}
    same_word = {tuple(terms(word)): word for word in given}
    concepts = dict(given)
    for word, concept in proposed.items():
        left = tuple(term for term in concept.abbreviations if term not in taken)
        word_given = same_word.get(tuple(terms(word)))
        if word_given is not None:
            written = (*given[word_given].abbreviations, *left)
            concepts[word_given] = replace(given[word_given], abbreviations=written)
        elif left or not (concept.abbreviations or word in taken):
            concepts[word] = replace(concept, abbreviations=left)
    return concepts


FORMAT: Final = Format(Overrides, Version(7, 6))
"""The format of the overrides, its version raised as `documents` says."""
