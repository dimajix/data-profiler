"""The stage describe: the names of the tables and columns of a profile read, its columns described.

Its steps follow one another, each filling attributes of the profile of its own and keeping all
others. The first splits each name into its terms, those written together by the vocabulary of the
profile, and gives each term its candidates, the concepts written as it; by these terms, it drops
from the glossary the abbreviations no name has any longer, and a concept no name is written as any
longer, by its word or an abbreviation. The second asks the language model for a concept of each
term of none, shown the names it appears in: a word and a description, which go into the glossary of
the profile; a word the glossary has takes the term as one more abbreviation of its concept. The
names are then split again, so that the concepts proposed are candidates, and the third step reads
each name. A reading is kept while the terms of its name are as they were split before, their
candidates among them, and agree with it, so that a reading chosen is not lost by a split that
stayed the same, and a term that gained a candidate has its name read anew. Else a name whose terms
have one candidate each, or are of digits, is read by them; one of a term of several, the language
model reads, shown the candidates with their descriptions, choosing for each such term one of them;
and any other, of a term of none, is left unread. The terms a split finds are written with the
readings of their names alone, table by table, so that the profile never holds a reading of other
terms than its own. The fourth asks the language model for the description of each column of none,
shown the reading of its name with the descriptions of its concepts, what is counted of it, its
values and those of its sample, the columns beside it and those filled together with it, and the key
it refers to, with the reading of the name of that table.

The steps see the profile with the overrides laid over it, so that the concepts given count and no
term of one, no name of a reading given and no column of a description given is asked for; but they
fill the profile as it was read, which holds nothing of the overrides. Every question shows the
model what the database holds, and what the tables it is of hold, where the overrides give it. The
language model is asked only for what the profile lacks, and the profile is written after each
concept proposed and each table read or described, so that a run interrupted is resumed by the next;
`forgotten` drops what the steps of the language model filled, to describe a profile anew, by
another model. The model sees the values of the samples of a column, but their nulls and sentinels,
as far as the module `disclosure` lets the profile hold them, as what it answers goes into the
profile; an answer not of the form asked for is passed over, with a warning. Without a language
model, the steps that ask it are left out: the glossary loses what no name has, and the names are
split and read by the candidates of their terms alone, but no concept is proposed, no reading chosen
and no column described, while what a model filled before is kept; the profile is written once, at
the end, as nothing is asked that a run interrupted would lose.

The questions to the model are Jinja2 templates in `data_profiler/templates/prompts/`, one of each,
holding as much of it as they can - its text, its conditions and its loops -, and what they share,
how a column is shown, a macro of its own. The code gives a template the objects it shows, and the
values of a sample only as the module `disclosure` lets them be shown, never the sample itself, and
renders it in a sandbox that refuses attributes of an underscore, so that a template changed shows
no value withheld.
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import islice
from pathlib import Path
from typing import Final

from jinja2 import PackageLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
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

# The prompts, each a template of its own: rendered as text, nothing escaped, as a prompt is no
# HTML, and no name left undefined; in a sandbox, which refuses attributes of an underscore, so that
# no template reaches a sample past `_Asking._values`.
_PROMPTS: Final = SandboxedEnvironment(
    loader=PackageLoader("data_profiler", "templates/prompts"),
    autoescape=False,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def describe(
    profile: Profile,
    overrides: Overrides,
    llm: LanguageModel | None,
    workspace: Workspace,
    directory: Path,
) -> None:
    """Describes `profile` into `directory`: concepts proposed, names read, columns described.

    The profile is written after each concept proposed, after each table whose names are split and
    read anew, the terms and readings of a table together, and after each table a column of which
    is described; without a language model, once, at the end.

    Args:
        profile: The profile, as it was read from `directory`, or as `forgotten` left it.
        overrides: The overrides of the project, whose concepts, readings and descriptions count
            beside those of the profile.
        llm: The language model that proposes the concepts, reads the names and describes the
            columns, or None to ask none.
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
    profile = _held(profile, overrides)
    if llm is None:
        _logger.info("Describing without a language model: no concept proposed or column described")
        profile = _names_kept(profile, overrides)
    else:
        asking = _Asking(overrides, llm, workspace, directory, profile.types)
        profile = asking.described(asking.names_read(asking.proposed(profile)))
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


def _split(profile: Profile, overrides: Overrides) -> Profile:
    """`profile`, each name split into its terms, by the concepts of it and of `overrides`."""
    laid = overrides.laid_over(profile)
    vocabulary = Vocabulary.of(laid)
    glossary = Glossary(laid.glossary)
    tables = []
    for table in profile.tables:
        columns = tuple(_terms(column, vocabulary, glossary) for column in table.columns)
        tables.append(_terms(replace(table, columns=columns), vocabulary, glossary))
    return replace(profile, tables=tuple(tables))


def _terms[Named: (Table, Column)](
    named: Named, vocabulary: Vocabulary, glossary: Glossary
) -> Named:
    """`named`, its name split into its terms, each with its candidates."""
    return replace(named, terms=glossary.terms(named.name, vocabulary))


def _held(profile: Profile, overrides: Overrides) -> Profile:
    """`profile`, of its concepts those a name has a term of, without the abbreviations none has.

    The names are split, by the concepts of it and of `overrides`, to find the terms they have,
    but stay as they are, so that the profile holds no terms of other readings than its own.
    """
    split = _split(profile, overrides)
    names: list[Table | Column] = [*split.tables]
    names += [column for table in split.tables for column in table.columns]
    held = {term.text for named in names for term in named.terms or ()}
    glossary = {}
    for word, concept in profile.glossary.items():
        if any(term in held for term in written_as(word, concept)):
            left = tuple(term for term in concept.abbreviations if term in held)
            glossary[word] = replace(concept, abbreviations=left)
    return replace(profile, glossary=glossary)


def _names_kept(profile: Profile, overrides: Overrides) -> Profile:
    """`profile`, its names split anew, by the concepts of it and of `overrides`, and `_kept`."""
    split = _split(profile, overrides)
    tables = []
    for before, table in zip(profile.tables, split.tables, strict=True):
        pairs = zip(before.columns, table.columns, strict=True)
        columns = tuple(_kept(old, column) for old, column in pairs)
        tables.append(_kept(before, replace(table, columns=columns)))
    return replace(split, tables=tuple(tables))


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


class _Asking:
    """The steps of describe that ask the language model, shown the samples of the workspace."""

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

    def proposed(self, profile: Profile) -> Profile:
        """`profile`, a concept proposed of each term of none, written after each.

        The names are split to find the terms of none, but the profile is written as it was but
        its glossary, so that it holds no terms of other readings than its own.
        """
        split = _split(profile, self._overrides)
        # The places with the overrides laid over them, so that the marks given count.
        for term, found in unknown(self._overrides.laid_over(split)).items():
            prompt = self._prompt("concept.txt", term=term, places=found)
            proposal = self._asked(prompt, _PROPOSAL, _PROPOSAL.json_schema())
            word = snake_case(proposal.word) if proposal is not None else ""
            if proposal is None or not word:
                _logger.warning("No concept was proposed of the term %s", term)
                continue
            concept = profile.glossary.get(word)
            if concept is None:
                abbreviations = () if term in written_as(word, Concept()) else (term,)
                concept = Concept(abbreviations, proposal.description.strip() or None)
            else:
                # Its own word only where the concept was dropped for an abbreviation given: the
                # term is then what keeps it, or the model would be asked of it at every run.
                concept = replace(concept, abbreviations=(*concept.abbreviations, term))
            profile = replace(profile, glossary={**profile.glossary, word: concept})
            profile.write(self._directory)
            _logger.info("Proposed the concept %s of the term %s", word, term)
        return profile

    def names_read(self, profile: Profile) -> Profile:
        """`profile`, its names split, and read: by `_names_kept`, else by the language model.

        The model is asked for a name where it is read by neither, none is given, and each of its
        terms has a candidate; the profile is written after each table split or read otherwise
        than before, its terms and readings together.
        """
        kept = _names_kept(profile, self._overrides)
        tables = list(kept.tables)
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
                replace(profile, tables=(*tables[: index + 1], *profile.tables[index + 1 :])).write(
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
                    None if given.description else self._description(given, shown, laid, glossary)
                )
                columns.append(replace(column, description=description or column.description))
            table = replace(tables[index], columns=tuple(columns))
            if table != tables[index]:
                tables[index] = table
                replace(profile, tables=tuple(tables)).write(self._directory)
        return replace(profile, tables=tuple(tables))

    def _description(
        self, column: Column, table: Table, profile: Profile, glossary: Glossary
    ) -> str | None:
        """The description the model proposes of `column`, of `table`, or None where it gives none.

        Args:
            column: The column, with the overrides laid over it.
            table: Its table, with the overrides laid over it.
            profile: The profile, with the overrides laid over it, of the table a column refers to.
            glossary: The concepts, those of the overrides among them.
        """
        prompt = self._prompt(
            "description.txt", column=column, table=table, profile=profile, glossary=glossary
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
        terms = list(zip(keys, found, strict=True))
        choices = {key: term.candidates for key, term in terms if len(term.candidates) > 1}
        prompt = self._prompt(
            "reading.txt", named=named, table=table, terms=terms, choices=choices, glossary=glossary
        )
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

    def _prompt(self, name: str, **shown: object) -> str:
        """The prompt of the template `name`, of what is `shown`, the database and the samples."""
        return _PROMPTS.get_template(name).render(
            **shown,
            # Of the overrides, as the profile read holds none, nor the profile laid over another.
            database=self._overrides.description,
            values=self._values,
            beside=_beside,
            end=_end,
            places_shown=_PLACES,
            columns_shown=_COLUMNS,
            enumerated_shown=_ENUMERATED,
        )

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


def _end(value: object) -> str:
    """An end of a range, as a prompt shows it: written as Python writes it, or not shown."""
    return "not shown" if value is None else repr(value)


def _beside(column: Column, table: Table) -> list[str]:
    """The names of the columns beside `column` in `table`, a few on either side, in their order."""
    names = [found.name for found in table.columns]
    index = names.index(column.name)
    return names[max(0, index - _NEIGHBOURS) : index] + names[index + 1 : index + 1 + _NEIGHBOURS]
