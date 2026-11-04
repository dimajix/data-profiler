"""The stage describe: the names of the tables and columns of a profile read, its columns described.

Its steps follow one another, each filling attributes of the profile of its own and keeping all
others. The first splits each name into its terms, those written together by the vocabulary of the
profile, and gives each term its candidates, the concepts written as it. The second asks the
language model for a concept of each term of none, shown the names it appears in: a word and a
description, which go into the glossary of the profile; a word the glossary has takes the term as
one more abbreviation of its concept. It drops first the abbreviations no name has any longer, and a
concept no name is written as any longer, by its word or an abbreviation. The names are then split
again, so that the concepts proposed are candidates, and the third step reads each name. A reading
is kept while the terms of its name are as they were split before, their candidates among them, and
agree with it, so that a reading chosen is not lost by a split that stayed the same, and a term that
gained a candidate has its name read anew. Else a name whose terms have one candidate each, or are
of digits, is read by them; one of a term of several, the language model reads, shown the candidates
with their descriptions, choosing for each such term one of them; and any other, of a term of none,
is left unread. The terms a split finds are written with the readings of their names alone, table by
table, so that the profile never holds a reading of other terms than its own. The fourth asks the
language model for the description of each column of none, shown the reading of its name with the
descriptions of its concepts, what is counted of it, its values and those of its sample, the columns
beside it and those filled together with it.

The steps see the profile with the overrides laid over it, so that the concepts given count and no
term of one, no name of a reading given and no column of a description given is asked for; but they
fill the profile as it was read, which holds nothing of the overrides. The language model is asked
only for what the profile lacks, and the profile is written after each concept proposed and each
table read or described, so that a run interrupted is resumed by the next; `forgotten` drops what
the steps of the language model filled, to describe a profile anew, by another model. The model sees
the values of the samples of a column, but their nulls and sentinels, as far as the module
`disclosure` lets the profile hold them, as what it answers goes into the profile; an answer not of
the form asked for is passed over, with a warning.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import islice
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter, ValidationError

from data_profiler.detect import SemanticType, is_filled
from data_profiler.disclosure import disclose_texts
from data_profiler.glossary import Glossary, Vocabulary, agrees, snake_case, unknown, written_as
from data_profiler.llm import LanguageModel
from data_profiler.overrides import Overrides
from data_profiler.profile import Column, Concept, Profile, Table
from data_profiler.values import as_text
from data_profiler.workspace import Sample, Workspace

_logger = logging.getLogger(__name__)

# The names a term is shown in, the values of a sample shown of a column, the values of an
# enumeration shown with their rows, the columns shown beside a column on either side, and the
# columns shown of a table: enough for the model to tell what a name stands for, few enough for its
# context.
_PLACES: Final = 20
_VALUES: Final = 3
_ENUMERATED: Final = 20
_NEIGHBOURS: Final = 3
_COLUMNS: Final = 20


@dataclass(frozen=True)
class _Proposal:
    """A concept proposed by the language model: its word and its description."""

    word: str
    description: str


_PROPOSAL: Final = TypeAdapter(_Proposal)


@dataclass(frozen=True)
class _Description:
    """A description of a column proposed by the language model."""

    description: str


_DESCRIPTION: Final = TypeAdapter(_Description)

# The concepts chosen by the language model, by the keys of the terms they are chosen of; which
# words may be chosen, the form of each question says.
_CHOICES: Final = TypeAdapter(dict[str, str])

# The words of the glossary are not shown: a small model shown them takes one of them for every
# term after.
_CONCEPT_PROMPT: Final = """\
You help to document the tables of a database whose names are made of English abbreviations.
The abbreviation "{term}" appears in these names of tables and columns, each column with its type,
what it was recognised as, and a few of its values:

{places}

Which English word, or few words, does "{term}" stand for in all of them? An abbreviation is mostly
the word shortened, its letters in the order of the word: "cd" for "code", "qty" for "quantity".
Answer with the word alone, in lower case, without the abbreviation, and describe in one sentence
what the word means, not the abbreviation, for a person who knows the business but not the
database.
"""

_READING_PROMPT: Final = """\
You help to document the tables of a database whose names are made of English abbreviations.
{subject}

Its name is made of these terms, in their order, each the word or an abbreviation of a concept:

{terms}

Some of them may stand for one of several concepts. Which concept does each of those stand for in
this name? Answer for each with the word of its concept.
"""


_DESCRIPTION_PROMPT: Final = """\
You help to document the tables of a database whose names are made of English abbreviations.
Here is what is known of the column "{column}" of the table "{table}":

{facts}

Describe in one or two sentences what the column holds, for a person who knows the business but
not the database. Do not repeat its name, and do not make up what the facts do not say.
"""


def describe(
    profile: Profile,
    overrides: Overrides,
    llm: LanguageModel,
    workspace: Workspace,
    directory: Path,
) -> None:
    """Describes `profile` into `directory`: concepts proposed, names read, columns described.

    The profile is written after each concept proposed, after each table whose names are split and
    read anew, the terms and readings of a table together, and after each table a column of which
    is described.

    Args:
        profile: The profile, as it was read from `directory`, or as `forgotten` left it.
        overrides: The overrides of the project, whose concepts, readings and descriptions count
            beside those of the profile.
        llm: The language model that proposes the concepts, reads the names and describes the
            columns.
        workspace: Where the samples of the tables are, whose values the model is shown.
        directory: The directory of the profile.

    Raises:
        OverridesError: The overrides name what the profile does not have, as
            `Overrides.laid_over` says.
        LanguageModelError: The language model fails to answer.
        WorkspaceError: The sample of a table cannot be read.
        ProfileError: The profile cannot be written.
    """
    overrides.warn_unused(profile)
    describing = _Describing(overrides, llm, workspace, directory, profile.types)
    profile = describing.described(describing.names_read(describing.proposed(profile)))
    profile.write(directory)
    columns = [column for table in profile.tables for column in table.columns]
    readings = [table.reading for table in profile.tables] + [c.reading for c in columns]
    _logger.info(
        "Described %d tables: %d of %d names read, %d of %d columns described, %d concepts",
        len(profile.tables),
        sum(reading is not None for reading in readings),
        len(readings),
        sum(column.description is not None for column in columns),
        len(columns),
        len(profile.glossary),
    )


def forgotten(profile: Profile) -> Profile:
    """`profile` without what the steps of the language model filled, to be described anew.

    Args:
        profile: The profile.

    Returns:
        The profile without its glossary, the readings of its names and the descriptions of its
        columns; its terms are split anew by `describe` in any case.
    """
    tables = (
        replace(
            table,
            reading=None,
            columns=tuple(
                replace(column, reading=None, description=None) for column in table.columns
            ),
        )
        for table in profile.tables
    )
    return replace(profile, tables=tuple(tables), glossary={})


def _terms[Named: (Table, Column)](
    named: Named, vocabulary: Vocabulary, glossary: Glossary
) -> Named:
    """`named`, its name split into its terms, each with its candidates."""
    return replace(named, terms=glossary.terms(named.name, vocabulary))


def _kept[Named: (Table, Column)](before: Named, named: Named) -> Named:
    """`named`, split anew, its reading kept where its terms are those of `before` and agree.

    Else it is read by the one candidate of each term, where each has one, and else unread: a term
    that gained a candidate has its name read anew.
    """
    if named.terms == before.terms and agrees(named.terms, named.reading):
        return named
    if named.terms is None or any(len(term.candidates) != 1 for term in named.terms):
        return replace(named, reading=None)
    return replace(named, reading=tuple(term.candidates[0] for term in named.terms))


class _Describing:
    """The steps of describe on a profile, by the overrides, the language model and the samples."""

    def __init__(
        self,
        overrides: Overrides,
        llm: LanguageModel,
        workspace: Workspace,
        directory: Path,
        types: Sequence[SemanticType],
    ) -> None:
        """Takes the overrides, the model, the samples, where to write, and the types of values."""
        self._overrides = overrides
        self._llm = llm
        self._workspace = workspace
        self._directory = directory
        self._types = types
        self._samples: dict[str, Sample] = {}

    def split(self, profile: Profile) -> Profile:
        """`profile`, each name split into its terms, by the concepts of it and of the overrides."""
        laid = self._overrides.laid_over(profile)
        vocabulary = Vocabulary.of(laid)
        glossary = Glossary(laid.glossary)
        tables = []
        for table in profile.tables:
            columns = tuple(_terms(column, vocabulary, glossary) for column in table.columns)
            tables.append(_terms(replace(table, columns=columns), vocabulary, glossary))
        return replace(profile, tables=tuple(tables))

    def proposed(self, profile: Profile) -> Profile:
        """`profile`, a concept proposed of each term of none, written after each.

        The names are split to find the terms of none, but the profile is written as it was but
        its glossary, so that it holds no terms of other readings than its own.
        """
        split = self.split(profile)
        profile = replace(profile, glossary=_held(split).glossary)
        # The places with the overrides laid over them, so that the marks given count.
        for term, found in unknown(self._overrides.laid_over(split)).items():
            lines = []
            for table, named, where in found[:_PLACES]:
                if isinstance(named, Table):
                    lines.append(f"- table {where}")
                else:
                    lines.append(f"- column {where}: {self._brief(table, named)}")
            prompt = _CONCEPT_PROMPT.format(term=term, places="\n".join(lines))
            proposal = self._asked(prompt, _PROPOSAL, _PROPOSAL.json_schema())
            word = snake_case(proposal.word) if proposal is not None else ""
            if proposal is None or not word:
                _logger.warning("No concept was proposed of the term %s", term)
                continue
            concept = profile.glossary.get(word)
            if concept is None:
                concept = Concept((term,), proposal.description.strip() or None)
            else:
                concept = replace(concept, abbreviations=(*concept.abbreviations, term))
            profile = replace(profile, glossary={**profile.glossary, word: concept})
            profile.write(self._directory)
            _logger.info("Proposed the concept %s of the term %s", word, term)
        return profile

    def names_read(self, profile: Profile) -> Profile:
        """`profile`, its names split, and read: by `_kept`, else by the language model.

        The model is asked for a name where it is read by neither, none is given, and each of its
        terms has a candidate; the profile is written after each table split or read otherwise
        than before, its terms and readings together.
        """
        split = self.split(profile)
        tables = []
        for before, table in zip(profile.tables, split.tables, strict=True):
            pairs = zip(before.columns, table.columns, strict=True)
            kept_columns = tuple(_kept(old, column) for old, column in pairs)
            tables.append(_kept(before, replace(table, columns=kept_columns)))
        kept = replace(split, tables=tuple(tables))
        laid = self._overrides.laid_over(kept)
        glossary = Glossary(laid.glossary)
        for index, shown in enumerate(laid.tables):
            table = tables[index]
            columns = tuple(
                replace(column, reading=self._choice(given, shown, glossary) or column.reading)
                for column, given in zip(table.columns, shown.columns, strict=True)
            )
            reading = self._choice(shown, shown, glossary) or table.reading
            tables[index] = replace(table, columns=columns, reading=reading)
            if tables[index] != profile.tables[index]:
                replace(profile, tables=(*tables, *profile.tables[index + 1 :])).write(
                    self._directory
                )
        return replace(profile, tables=tuple(tables))

    def described(self, profile: Profile) -> Profile:
        """`profile`, each of its columns of no description described by the language model.

        A column of a description given is not asked for; the profile is written after each table
        a column of which was described.
        """
        laid = self._overrides.laid_over(profile)
        glossary = Glossary(laid.glossary)
        tables = list(profile.tables)
        for index, shown in enumerate(laid.tables):
            columns = []
            for column, given in zip(tables[index].columns, shown.columns, strict=True):
                description = (
                    None if given.description else self._description(given, shown, glossary)
                )
                columns.append(replace(column, description=description or column.description))
            table = replace(tables[index], columns=tuple(columns))
            if table != tables[index]:
                tables[index] = table
                replace(profile, tables=tuple(tables)).write(self._directory)
        return replace(profile, tables=tuple(tables))

    def _description(self, column: Column, table: Table, glossary: Glossary) -> str | None:
        """The description the model proposes of `column`, of `table`, or None where it gives none.

        Args:
            column: The column, with the overrides laid over it.
            table: Its table, with the overrides laid over it.
            glossary: The concepts, those of the overrides among them.
        """
        facts = []
        name = glossary.harmonized(column)
        if name is not None:
            facts.append(f"- its name reads: {name}")
        for word in dict.fromkeys(column.reading or ()):
            concept = glossary.concept(word)
            if concept is not None and concept.description:
                facts.append(f"- {word}: {concept.description}")
        named = glossary.harmonized(table)
        if named is not None:
            facts.append(f"- the name of the table reads: {named}")
        facts.append(f"- type: {self._brief(table, column)}")
        facts.extend(_statistics(column, table))
        facts.append(f"- the columns beside it: {', '.join(_beside(column, table)) or 'none'}")
        for group in table.groups:
            if column.name in group.columns:
                together = [other for other in group.columns if other != column.name]
                facts.append(f"- filled in the same rows as: {', '.join(together)}")
        prompt = _DESCRIPTION_PROMPT.format(
            column=column.name, table=table.name, facts="\n".join(facts)
        )
        answer = self._asked(prompt, _DESCRIPTION, _DESCRIPTION.json_schema())
        description = answer.description.strip() if answer is not None else ""
        if not description:
            _logger.warning(
                "No description was proposed of the column %s.%s", table.name, column.name
            )
            return None
        _logger.info("Described the column %s.%s", table.name, column.name)
        return description

    def _choice(
        self, named: Table | Column, table: Table, glossary: Glossary
    ) -> tuple[str, ...] | None:
        """The reading the model chooses of the name of `named`, of `table`, as `names_read` says.

        Args:
            named: The table or column, with the overrides laid over it.
            table: Its table, with the overrides laid over it.
            glossary: The concepts, those of the overrides among them.

        Returns:
            The reading, or None where the model is not to be asked, or chooses no candidate.
        """
        found = named.terms
        if (
            found is None
            or named.reading is not None
            or any(not term.candidates for term in found)
            or all(len(term.candidates) == 1 for term in found)
        ):
            return None
        keys = [f"{place}_{term.text}" for place, term in enumerate(found, 1)]
        lines = []
        choices: dict[str, tuple[str, ...]] = {}
        for key, term in zip(keys, found, strict=True):
            if len(term.candidates) == 1:
                lines.append(f'- "{term.text}" ({key}): {term.candidates[0]}')
                continue
            choices[key] = term.candidates
            meanings = "; ".join(_meaning(word, glossary) for word in term.candidates)
            lines.append(f'- "{term.text}" ({key}): one of {meanings}')
        subject = self._subject(named, table)
        prompt = _READING_PROMPT.format(subject=subject, terms="\n".join(lines))
        properties = {
            key: {"type": "string", "enum": list(words)} for key, words in choices.items()
        }
        form = {"type": "object", "properties": properties, "required": list(choices)}
        chosen = self._asked(prompt, _CHOICES, form)
        if chosen is None or any(chosen.get(key) not in words for key, words in choices.items()):
            _logger.warning("No reading was chosen of the name %s", named.name)
            return None
        reading = tuple(
            chosen[key] if key in choices else term.candidates[0]
            for key, term in zip(keys, found, strict=True)
        )
        _logger.info("Read the name %s as %s", named.name, ", ".join(reading))
        return reading

    def _subject(self, named: Table | Column, table: Table) -> str:
        """What the question of the reading of the name of `named`, of `table`, is about."""
        if isinstance(named, Table):
            shown = ", ".join(column.name for column in table.columns[:_COLUMNS])
            more = ", ..." if len(table.columns) > _COLUMNS else ""
            return f'It is about the table "{table.name}", of the columns {shown}{more}.'
        beside = ", ".join(_beside(named, table)) or "none"
        return (
            f'It is about the column "{named.name}" of the table "{table.name}":'
            f" {self._brief(table, named)}. The columns beside it are {beside}."
        )

    def _brief(self, table: Table, column: Column) -> str:
        """The type of `column`, of `table`, what it was recognised as, and a few of its values."""
        parts = [column.type, *(f"recognised as {match.type.name}" for match in column.matches)]
        values = self._values(table, column)
        if column.sensitive:
            parts.append(f"{column.sensitivity.value} data, its values not shown")
        elif values:
            parts.append("values: " + ", ".join(values))
        return "; ".join(parts)

    def _values(self, table: Table, column: Column) -> list[str]:
        """A few distinct values of the sample of `column`, of `table`, as far as they are shown."""
        if table.name not in self._samples:
            self._samples[table.name] = self._workspace.read_sample(table.name)
        found = self._samples[table.name].columns.get(column.name, ())
        # Each distinct value once, and judged only until enough are shown.
        texts = dict.fromkeys(
            as_text(value) for value in found if is_filled(value, column.left_aside)
        )
        return list(islice(disclose_texts(column, texts, self._types), _VALUES))

    def _asked[T](
        self, prompt: str, adapter: TypeAdapter[T], form: Mapping[str, object]
    ) -> T | None:
        """The answer to `prompt` in `form`, parsed by `adapter`, or None where it is not of it."""
        answer = self._llm.answer(prompt, form)
        try:
            return adapter.validate_json(answer)
        except ValidationError:
            _logger.warning("An answer of %s was not of the form asked for", self._llm.name)
            return None


def _statistics(column: Column, table: Table) -> list[str]:
    """What is counted of `column`, of `table`, as lines of facts."""
    statistics = column.statistics
    facts = []
    facts.append(
        f"- rows of the table: {table.rows}, of them null: {statistics.nulls},"
        f" holding a value that stands for none: {statistics.sentinel_rows}"
    )
    facts.append(f"- distinct values: {statistics.distinct}")
    if statistics.lengths is not None:
        lengths = statistics.lengths
        facts.append(f"- lengths: {lengths.shortest} to {lengths.longest}")
    if statistics.range is not None:
        ends = (statistics.range.smallest, statistics.range.largest)
        smallest, largest = ("not shown" if end is None else repr(end) for end in ends)
        facts.append(f"- range: {smallest} to {largest}")
    if column.values:
        counted = ", ".join(
            f"{value.value} ({value.rows})" for value in column.values[:_ENUMERATED]
        )
        facts.append(f"- its values, with their rows: {counted}")
    return facts


def _beside(column: Column, table: Table) -> list[str]:
    """The names of the columns beside `column` in `table`, a few on either side, in their order."""
    names = [found.name for found in table.columns]
    index = names.index(column.name)
    return names[max(0, index - _NEIGHBOURS) : index] + names[index + 1 : index + 1 + _NEIGHBOURS]


def _meaning(word: str, glossary: Glossary) -> str:
    """`word`, with the description of its concept in parentheses, where it has one."""
    concept = glossary.concept(word)
    return f"{word} ({concept.description})" if concept and concept.description else word


def _held(profile: Profile) -> Profile:
    """`profile`, its concepts of a term a name has alone, without the abbreviations no name has."""
    names: list[Table | Column] = [*profile.tables]
    names += [column for table in profile.tables for column in table.columns]
    held = {term.text for named in names for term in named.terms or ()}
    glossary = {}
    for word, concept in profile.glossary.items():
        if any(term in held for term in written_as(word, concept)):
            left = tuple(term for term in concept.abbreviations if term in held)
            glossary[word] = replace(concept, abbreviations=left)
    return replace(profile, glossary=glossary)
