"""The glossary: original names split into terms, and harmonized names composed from their words.

An original name - of a table or of a column - is split into its terms at everything that is no
letter and no digit, at a change from a lower case letter to an upper case one, before the last of
several upper case letters that a lower case one follows, and between letters and digits:
`CUST_CRT_DT` into `cust`, `crt` and `dt`, `custCrtDt` and `CUSTCrtDt` alike, `addr2` into `addr`
and `2`. A term is in lower case, so that `CUST` and `cust` are one.

The glossary of a profile is its concepts, each a word with the terms it is written as, its
abbreviations, once for the whole schema. A term stands for the concept it is an abbreviation of;
one of several concepts, for none yet that is known. A harmonized name is composed of the words of
the concepts of the terms of the original name, each word split as a name is, in `snake_case`: a
term of digits stands for itself, and a concept omitted is left out.
"""

import re
import unicodedata
from collections.abc import Mapping
from typing import Final

from data_profiler.profile import Concept, Profile, Table

# What separates the terms of a name, whatever else splits them: anything but letters and digits.
_SEPARATORS: Final = re.compile(r"[\W_]+")


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
        Each term that needs a concept, in the order it first appears, with the names it appears in,
        in their order: a table by its name, a column as `table.column`, each once. A term of
        digits needs none, as it stands for itself.
    """
    found: dict[str, list[str]] = {}
    for table in profile.tables:
        names = [(table.name, table.name)]
        names += [(column.name, f"{table.name}.{column.name}") for column in table.columns]
        for name, where in names:
            for term in dict.fromkeys(terms(name)):
                if not term.isdigit():
                    found.setdefault(term, []).append(where)
    return found


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

    def harmonized(self, name: str) -> str | None:
        """The harmonized name of `name`: the words of the concepts of its terms, in snake_case.

        Args:
            name: The original name, of a table or a column.

        Returns:
            The harmonized name, without the words of the concepts omitted; None while a term of
            the name is of no concept, or of several, or has a word of neither letters nor
            digits, or where no word is left.
        """
        words = []
        for term in terms(name):
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

    def collisions(self, table: Table) -> dict[str, tuple[str, ...]]:
        """Each harmonized name of two columns of `table` or more, with their original names.

        Args:
            table: The table.

        Returns:
            Each harmonized name that two columns or more have, in the order of the table, with
            the names of those columns, in their order.
        """
        found: dict[str, list[str]] = {}
        for column in table.columns:
            name = self.harmonized(column.name)
            if name is not None:
                found.setdefault(name, []).append(column.name)
        return {name: tuple(columns) for name, columns in found.items() if len(columns) > 1}
