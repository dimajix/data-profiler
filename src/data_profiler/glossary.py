"""The glossary: original names split into terms, and harmonized names composed from their words.

An original name - of a table or of a column - is split into its terms at everything that is no
letter and no digit, at a change from a lower case letter to an upper case one, before the last of
several upper case letters that a lower case one follows, and between letters and digits:
`CUST_CRT_DT` into `cust`, `crt` and `dt`, `custCrtDt` and `CUSTCrtDt` alike, `addr2` into `addr`
and `2`. A term is in lower case, so that `CUST` and `cust` are one.

Terms written together without anything that separates them - `lfadr` in `KD_LFADR_PLZ` - are
split by the vocabulary of the profile: the terms found in its names, and the abbreviations of its
concepts. A term is split where other terms of the vocabulary, of two characters at least, cover it
whole, into the fewest of them, the longer first where two splits have as many; each part is split
again the same way. Where they leave a character uncovered, it stays whole: a split of a term
covered in part would split most abbreviations, `strt` into `st` and `rt`. An abbreviation of a
concept is never split, so that a person stops a wrong split by giving the term a concept.

The glossary of a profile is its concepts, each a word with the terms it is written as, its
abbreviations, once for the whole schema. A term stands for the concept it is an abbreviation of;
one of several concepts, for none yet that is known. A harmonized name is composed of the words of
the concepts of the terms of the original name, each word split as a name is, in `snake_case`: a
term of digits stands for itself, and a concept omitted is left out.
"""

import re
import unicodedata
from collections.abc import Collection, Mapping
from typing import Final, Self

from data_profiler.profile import Concept, Profile, Table

# What separates the terms of a name, whatever else splits them: anything but letters and digits.
_SEPARATORS: Final = re.compile(r"[\W_]+")

# The fewest characters of a part a term written together is split into.
_SHORTEST: Final = 2


def terms(name: str) -> list[str]:
    """The terms of the original name `name`, in lower case, in their order.

    Args:
        name: The name, of a table or a column; or a word, whose terms make it snake_case.

    Returns:
        The terms; none of a name without letters and digits.
    """
    found = []
    # Composed, so that a letter with its accent is one character, as in most names it is.
    for part in _SEPARATORS.split(unicodedata.normalize("NFC", name)):
        start = 0
        for index in range(1, len(part)):
            if _splits(part, index):
                found.append(part[start:index].lower())
                start = index
        if part:
            found.append(part[start:].lower())
    return found


def _splits(part: str, index: int) -> bool:
    """Whether a term of `part`, a name without separators, begins at `index`."""
    before, at = part[index - 1], part[index]
    after = part[index + 1 : index + 2]
    return (
        before.isdigit() != at.isdigit()
        or (before.islower() and at.isupper())
        or (before.isupper() and at.isupper() and after.islower())
    )


def occurrences(profile: Profile) -> dict[str, list[str]]:
    """Each term of the names of the tables and columns of `profile`, with the names it appears in.

    Args:
        profile: The profile.

    Returns:
        Each term that needs a concept, as the vocabulary of the profile splits the names, in the
        order it first appears, with the names it appears in, in their order: a table by its name,
        a column as `table.column`, each once. A term of digits needs none, as it stands for
        itself.
    """
    vocabulary = Vocabulary.of(profile)
    found: dict[str, list[str]] = {}
    for table in profile.tables:
        names = [(table.name, table.name)]
        names += [(column.name, f"{table.name}.{column.name}") for column in table.columns]
        for name, where in names:
            for term in dict.fromkeys(vocabulary.split(name)):
                if not term.isdigit():
                    found.setdefault(term, []).append(where)
    return found


class Vocabulary:
    """The terms a term written together is split into, of a profile.

    They are the terms found in its names and the abbreviations of its concepts, which are never
    split.
    """

    def __init__(self, found: Collection[str], abbreviations: Collection[str]) -> None:
        """Takes the terms found in the names, and the abbreviations of the concepts."""
        self._kept = frozenset(abbreviations)
        self._parts = frozenset(t for t in (*found, *abbreviations) if len(t) >= _SHORTEST)

    @classmethod
    def of(cls, profile: Profile) -> Self:
        """The vocabulary of `profile`: the terms of its names, and its abbreviations.

        Args:
            profile: The profile.

        Returns:
            The vocabulary, of the terms `terms` finds in the names of the tables and columns, but
            those of digits, and of the abbreviations of the concepts.
        """
        names = [table.name for table in profile.tables]
        names += [column.name for table in profile.tables for column in table.columns]
        found = {term for name in names for term in terms(name) if not term.isdigit()}
        abbreviations = {t for concept in profile.glossary.values() for t in concept.abbreviations}
        return cls(found, abbreviations)

    def split(self, name: str) -> list[str]:
        """The terms of `name`, as `terms` gives them, those written together split.

        Args:
            name: The original name, of a table or a column.

        Returns:
            The terms, in lower case, in their order.
        """
        return [part for term in terms(name) for part in self._split(term)]

    def _split(self, term: str) -> list[str]:
        """The parts of `term`, itself where the vocabulary does not cover it whole."""
        if term in self._kept or term.isdigit():
            return [term]
        parts = self._fewest(term)
        if parts is None:
            return [term]
        return [found for part in parts for found in self._split(part)]

    def _fewest(self, term: str) -> list[str] | None:
        """The fewest other terms of the vocabulary that cover `term` whole, or None where none do.

        Of two covers of as many terms, the one of the longer first term is taken.
        """
        # The fewest terms that cover the rest of `term` from each place on, or None.
        covers: list[list[str] | None] = [None] * len(term) + [[]]
        for start in range(len(term) - 1, -1, -1):
            for end in range(len(term), start, -1):
                part, rest = term[start:end], covers[end]
                if part == term or part not in self._parts or rest is None:
                    continue
                cover = covers[start]
                if cover is None or len(rest) + 1 < len(cover):
                    covers[start] = [part, *rest]
        return covers[0]


class Glossary:
    """The concepts of a profile by the terms they are written as: the words of its names."""

    def __init__(self, concepts: Mapping[str, Concept]) -> None:
        """Takes the concepts, by their words."""
        self._concepts = concepts
        self._words: dict[str, list[str]] = {}
        for word, concept in concepts.items():
            for term in dict.fromkeys(concept.abbreviations):
                self._words.setdefault(term, []).append(word)

    def words(self, term: str) -> tuple[str, ...]:
        """The words of the concepts `term` is an abbreviation of, in the order of the glossary.

        Args:
            term: A term, in lower case.

        Returns:
            The words; none where the term is of no concept.
        """
        return tuple(self._words.get(term, ()))

    def harmonized(self, parts: list[str]) -> str | None:
        """The harmonized name of a name split into `parts`: the words of their concepts.

        Args:
            parts: The terms of the original name, of a table or a column, as the vocabulary
                splits it.

        Returns:
            The harmonized name, without the words of the concepts omitted; None while a term of
            the name is of no concept, or of several, or has a word of neither letters nor
            digits, or where no word is left.
        """
        words = []
        for term in parts:
            if term.isdigit():
                words.append(term)
                continue
            found = self.words(term)
            if len(found) != 1:
                return None
            (word,) = found
            if self._concepts[word].omitted:
                continue
            composed = "_".join(terms(word))
            if not composed:
                return None
            words.append(composed)
        return "_".join(words) or None

    def collisions(self, table: Table, vocabulary: Vocabulary) -> dict[str, tuple[str, ...]]:
        """Each harmonized name of two columns of `table` or more, with their original names.

        Args:
            table: The table.
            vocabulary: The vocabulary the names of its columns are split by.

        Returns:
            Each harmonized name that two columns or more have, in the order of the table, with
            the names of those columns, in their order.
        """
        found: dict[str, list[str]] = {}
        for column in table.columns:
            name = self.harmonized(vocabulary.split(column.name))
            if name is not None:
                found.setdefault(name, []).append(column.name)
        return {name: tuple(columns) for name, columns in found.items() if len(columns) > 1}
