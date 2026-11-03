"""The stage describe: the names of the tables and columns of a profile split, given concepts, read.

Its steps follow one another, each filling attributes of the profile of its own and keeping all
others. The first splits each name into its terms, those written together by the vocabulary of the
profile, and gives each term its candidates, the concepts it is an abbreviation of. The second asks
the language model for a concept of each term of none, shown the names it appears in: a word and a
description, which go into the glossary of the profile; a word the glossary has takes the term as
one more abbreviation of its concept. It drops first the abbreviations no name has any longer, and
a concept left without any. The names are then split again, so that the concepts proposed are
candidates. The third reads each name: a reading that still agrees with the terms of its name is
kept, so that a reading chosen is not lost by a split that stayed the same; where it does not, a
name whose terms have one candidate each, or are of digits, is read by them, and any other is left
unread.

The steps see the profile with the overrides laid over it, so that the concepts given count and no
term of one is asked for, but fill the profile as it was read, which holds nothing of the overrides.
The language model is asked only for what the profile lacks, and the profile is written after
each concept proposed, so that a run interrupted is resumed by the next; `forgotten` drops what
the steps of the language model filled, to describe a profile anew, by another model. The model
sees the values of the samples of the columns of no sensitivity, but their nulls and sentinels, as
what it answers goes into the profile; an answer not of the form asked for is passed over, with a
warning.
"""

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter, ValidationError

from data_profiler.detect import is_filled
from data_profiler.glossary import Glossary, Vocabulary, agrees, terms, unknown
from data_profiler.model import Model
from data_profiler.overrides import Overrides
from data_profiler.profile import Column, Concept, Profile, Table
from data_profiler.values import as_text
from data_profiler.workspace import Sample, Workspace

_logger = logging.getLogger(__name__)

# The names a term is shown in, the values of a sample shown of a column, and the characters of
# each value shown: enough for the model to tell what a column holds, few enough for its context.
_PLACES: Final = 20
_VALUES: Final = 3
_LENGTH: Final = 40


@dataclass(frozen=True)
class _Proposal:
    """A concept proposed by the language model: its word and its description."""

    word: str
    description: str


_PROPOSAL: Final = TypeAdapter(_Proposal)

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


def describe(
    profile: Profile, overrides: Overrides, model: Model, workspace: Workspace, directory: Path
) -> None:
    """Describes `profile` into `directory`: its names split, concepts proposed, and names read.

    The profile is written after each step, and after each concept proposed.

    Args:
        profile: The profile, as it was read from `directory`, or as `forgotten` left it.
        overrides: The overrides of the project, whose concepts count beside those of the profile.
        model: The language model that proposes the concepts.
        workspace: Where the samples of the tables are, whose values the model is shown.
        directory: The directory of the profile.

    Raises:
        OverridesError: The overrides name what the profile does not have, as
            `Overrides.laid_over` says.
        ModelError: The language model fails to answer.
        WorkspaceError: The sample of a table cannot be read.
        ProfileError: The profile cannot be written.
    """
    profile = _split(profile, overrides)
    profile.write(directory)
    profile = _proposed(profile, overrides, model, workspace, directory)
    profile = _read(_split(profile, overrides))
    profile.write(directory)
    readings = [table.reading for table in profile.tables]
    readings += [column.reading for table in profile.tables for column in table.columns]
    read = sum(reading is not None for reading in readings)
    _logger.info(
        "Described the names of %d tables: %d of %d read, %d concepts in the glossary",
        len(profile.tables),
        read,
        len(readings),
        len(profile.glossary),
    )


def forgotten(profile: Profile) -> Profile:
    """`profile` without what the steps of the language model filled, to be described anew.

    Args:
        profile: The profile.

    Returns:
        The profile without its glossary and the readings of its names; its terms are split anew
        by `describe` in any case.
    """
    tables = (
        replace(
            table,
            reading=None,
            columns=tuple(replace(column, reading=None) for column in table.columns),
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


def _proposed(
    profile: Profile, overrides: Overrides, model: Model, workspace: Workspace, directory: Path
) -> Profile:
    """`profile`, a concept proposed of each term of none, written after each into `directory`."""
    profile = _held(profile)
    samples: dict[str, Sample] = {}
    # The places of the profile with the overrides laid over it, so that the marks given count.
    for term, found in unknown(overrides.laid_over(profile)).items():
        lines = []
        for table, named, where in found[:_PLACES]:
            if isinstance(named, Table):
                lines.append(f"- table {where}")
                continue
            if table.name not in samples:
                samples[table.name] = workspace.read_sample(table.name)
            lines.append(f"- column {where}{_brief(named, samples[table.name])}")
        prompt = _CONCEPT_PROMPT.format(term=term, places="\n".join(lines))
        proposal = _asked(model, prompt, _PROPOSAL)
        word = "_".join(terms(proposal.word)) if proposal is not None else ""
        if proposal is None or not word:
            _logger.warning("No concept was proposed of the term %s", term)
            continue
        concept = profile.glossary.get(word)
        if concept is None:
            concept = Concept((term,), proposal.description.strip() or None)
        else:
            concept = replace(concept, abbreviations=(*concept.abbreviations, term))
        profile = replace(profile, glossary={**profile.glossary, word: concept})
        profile.write(directory)
        _logger.info("Proposed the concept %s of the term %s", word, term)
    return profile


def _held(profile: Profile) -> Profile:
    """`profile`, its concepts without the abbreviations no name has, and without those of none."""
    names: list[Table | Column] = [*profile.tables]
    names += [column for table in profile.tables for column in table.columns]
    held = {term.text for named in names for term in named.terms or ()}
    glossary = {}
    for word, concept in profile.glossary.items():
        left = tuple(term for term in concept.abbreviations if term in held)
        if left:
            glossary[word] = replace(concept, abbreviations=left)
    return replace(profile, glossary=glossary)


def _brief(column: Column, sample: Sample) -> str:
    """The type of `column`, what it was recognised as, and a few values of its sample."""
    parts = [column.type, *(f"recognised as {match.type.name}" for match in column.matches)]
    if column.sensitive:
        parts.append(f"{column.sensitivity.value} data, its values not shown")
    else:
        found = sample.columns.get(column.name, ())
        values = (as_text(value) for value in found if is_filled(value, column.left_aside))
        shown = [value[:_LENGTH] for value in list(dict.fromkeys(values))[:_VALUES]]
        if shown:
            parts.append("values: " + ", ".join(shown))
    return f": {'; '.join(parts)}"


def _asked[T](model: Model, prompt: str, form: TypeAdapter[T]) -> T | None:
    """The answer of `model` to `prompt`, parsed by `form`, or None where it is not of the form."""
    answer = model.answer(prompt, form.json_schema())
    try:
        return form.validate_json(answer)
    except ValidationError:
        _logger.warning("An answer of %s was not of the form asked for", model.name)
        return None


def _read(profile: Profile) -> Profile:
    """`profile`, each of its names read where it can be."""
    tables = []
    for table in profile.tables:
        columns = tuple(_reading(column) for column in table.columns)
        tables.append(_reading(replace(table, columns=columns)))
    return replace(profile, tables=tuple(tables))


def _reading[Named: (Table, Column)](named: Named) -> Named:
    """`named`, its reading kept where it agrees with its terms, else read where it can be."""
    if agrees(named.terms, named.reading) or named.terms is None:
        return named
    if any(len(term.candidates) != 1 for term in named.terms):
        return replace(named, reading=None)
    return replace(named, reading=tuple(term.candidates[0] for term in named.terms))
