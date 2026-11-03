"""The stage describe: the names of the tables and columns of a profile split into terms, and read.

Its steps follow one another, each filling attributes of the profile of its own and keeping all
others. The first splits each name into its terms, those written together by the vocabulary of the
profile, and gives each term its candidates, the concepts it is an abbreviation of. The second
reads each name: a reading that still agrees with the terms of its name is kept, so that a reading
chosen is not lost by a split that stayed the same; where it does not, a name whose terms have one
candidate each, or are of digits, is read by them, and any other is left unread - which concept a
term of several stands for, the language model is to choose. The steps see the profile with the
overrides laid over it, so that the concepts given count, but fill the profile as it was read,
which holds nothing of the overrides.
"""

import logging
from dataclasses import replace

from data_profiler.glossary import Glossary, Vocabulary, agrees
from data_profiler.overrides import Overrides
from data_profiler.profile import Column, Profile, Table

_logger = logging.getLogger(__name__)


def describe(profile: Profile, overrides: Overrides) -> Profile:
    """`profile`, the names of its tables and columns split into their terms, and read.

    Args:
        profile: The profile, as it was read.
        overrides: The overrides of the project, whose concepts the names are split and read by.

    Returns:
        The profile, each table and column with the terms of its name and, where it is read, its
        reading; all else as it was.

    Raises:
        OverridesError: The overrides name what the profile does not have, as
            `Overrides.laid_over` says.
    """
    laid = overrides.laid_over(profile)
    vocabulary = Vocabulary.of(laid)
    glossary = Glossary(laid.glossary)
    tables = []
    for table in profile.tables:
        columns = tuple(_read(_split(column, vocabulary, glossary)) for column in table.columns)
        tables.append(_read(_split(replace(table, columns=columns), vocabulary, glossary)))
    readings = [table.reading for table in tables]
    readings += [column.reading for table in tables for column in table.columns]
    read = sum(reading is not None for reading in readings)
    _logger.info(
        "Split and read the names of %d tables: %d of %d read", len(tables), read, len(readings)
    )
    return replace(profile, tables=tuple(tables))


def _split[Named: (Table, Column)](
    named: Named, vocabulary: Vocabulary, glossary: Glossary
) -> Named:
    """`named`, its name split into its terms, each with its candidates."""
    return replace(named, terms=glossary.terms(named.name, vocabulary))


def _read[Named: (Table, Column)](named: Named) -> Named:
    """`named`, its reading kept where it agrees with its terms, else read where it can be."""
    if agrees(named.terms, named.reading) or named.terms is None:
        return named
    if any(len(term.candidates) != 1 for term in named.terms):
        return replace(named, reading=None)
    return replace(named, reading=tuple(term.candidates[0] for term in named.terms))
