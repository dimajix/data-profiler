"""The glossary: original names split into terms, and harmonized names composed from readings.

An original name - of a table or of a column - is split into its terms at everything that is no
letter and no digit, at a change from a lower case letter to an upper case one, before the last of
several upper case letters that a lower case one follows, and between letters and digits:
`CUST_CRT_DT` into `cust`, `crt` and `dt`, `custCrtDt` and `CUSTCrtDt` alike, `addr2` into `addr`
and `2`. A term is in lower case, so that `CUST` and `cust` are one.

Terms written together without anything that separates them - `lfadr` in `KD_LFADR_PLZ` - are
split by the vocabulary of the profile: the terms found in its names, and the terms its concepts are
written as. A term is split where other terms of the vocabulary, of two characters at least, cover
it whole, into the fewest of them, the longer first where two splits have as many; each part is
split again the same way. Where they leave a character uncovered, it stays whole: a split of a term
covered in part would split most abbreviations, `strt` into `st` and `rt`. A term a concept is
written as is never split, so that a person stops a wrong split by giving the term a concept.

The same holds across the cuts above: pieces of a name, one after the other, that are the pieces of
a term a concept is written as are that one term, however the name writes them - `3` and `rd` the
term `3rd` of `3rd_party`, `contract` and `item` the term `contract_item` of `ContractItem`. Where
such terms can be found in several ways, the fewest terms are taken, the longer first where two have
as many. A term is compared by its pieces, so that `manage` is not found in `man_age`.

The glossary of a profile is its concepts, once for the whole schema, each a word with the terms it
is written as: its word and its abbreviations - `customer` as `customer`, `cust` and `kd`,
`contact_person` as `contact_person` and `ap`. A term may stand for the concepts written as it, its
candidates; which one it stands for in a name, the reading of the name says, one word for each
term. A harmonized name is composed of the words of its reading, each in `snake_case`, which cuts
a word as a name is cut but not at digits, so that the word `b2b` stays whole: a term of digits
stands for itself, and a concept omitted is left out; a name given by hand comes before it. A
reading that no longer agrees with the terms of its name - of another length, or a word that is no
candidate of its term - is none.
"""

import re
import unicodedata
from collections.abc import Callable, Collection, Iterator, Mapping
from typing import Final, Self

from data_profiler.profile import Column, Concept, Profile, Table, Term

# What separates the terms of a name, whatever else splits them: anything but letters and digits.
_SEPARATORS: Final = re.compile(r"[\W_]+")

# The fewest characters of a part a term written together is split into.
_SHORTEST: Final = 2


def terms(name: str) -> list[str]:
    """The terms of the original name `name`, in lower case, in their order.

    Args:
        name: The name, of a table or a column; or a term of a concept, to compare its pieces.

    Returns:
        The terms; none of a name without letters and digits.
    """
    return _cut(name, _splits)


def snake_case(name: str) -> str:
    """`name` in snake_case: cut as `terms` cuts a name, but not at digits, and joined by `_`.

    Args:
        name: A name or a word.

    Returns:
        Its pieces joined by `_`, digits staying with the letters around them: `b2b` of `B2B`,
        `address2` of `Address2`; empty where it has no letters and digits.
    """
    return "_".join(_cut(name, _changes_case))


def _cut(name: str, cuts: Callable[[str, int], bool]) -> list[str]:
    """The pieces of `name`, in lower case: between its separators, and where `cuts` says."""
    found = []
    # Composed, so that a letter with its accent is one character, as in most names it is.
    for part in _SEPARATORS.split(unicodedata.normalize("NFC", name)):
        start = 0
        for index in range(1, len(part)):
            if cuts(part, index):
                found.append(part[start:index].lower())
                start = index
        if part:
            found.append(part[start:].lower())
    return found


def written_as(word: str, concept: Concept) -> tuple[str, ...]:
    """The terms a concept is written as: its word and its abbreviations.

    Args:
        word: The word of the concept.
        concept: The concept.

    Returns:
        The word in snake_case, then the abbreviations; the abbreviations alone where the word has
        no letters and digits.
    """
    own = snake_case(word)
    return (own, *concept.abbreviations) if own else concept.abbreviations


def _splits(part: str, index: int) -> bool:
    """Whether a term of `part`, a name without separators, begins at `index`."""
    return part[index - 1].isdigit() != part[index].isdigit() or _changes_case(part, index)


def _changes_case(part: str, index: int) -> bool:
    """Whether the case of `part`, a name without separators, says a piece begins at `index`."""
    before, at = part[index - 1], part[index]
    after = part[index + 1 : index + 2]
    return (before.islower() and at.isupper()) or (
        before.isupper() and at.isupper() and after.islower()
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
    for _, named, where in _places(profile):
        for term in dict.fromkeys(vocabulary.split(named.name)):
            if not term.isdigit():
                found.setdefault(term, []).append(where)
    return found


type Place = tuple[Table, Table | Column, str]
"""A table or column of a profile, with its table and where it is: a table by its name, a column as
`table.column`."""


def unknown(profile: Profile) -> dict[str, list[Place]]:
    """Each term of the names of `profile` of no concept, as describe split them, with its places.

    Args:
        profile: The profile, its names split.

    Returns:
        Each term without candidates, but of digits, among the terms of the names, in the order it
        first appears, with the tables and columns it appears in, in their order, each once; none
        of a name not split.
    """
    found: dict[str, list[Place]] = {}
    for place in _places(profile):
        named = place[1]
        for term in dict.fromkeys(term.text for term in named.terms or () if not term.candidates):
            found.setdefault(term, []).append(place)
    return found


def _places(profile: Profile) -> Iterator[Place]:
    """Each table, then each of its columns, of `profile`, in their order."""
    for table in profile.tables:
        yield table, table, table.name
        for column in table.columns:
            yield table, column, f"{table.name}.{column.name}"


def _fewest(length: int, piece: Callable[[int, int], str | None]) -> list[str] | None:
    """The fewest pieces that cover `length` places whole, or None where none do.

    Of two covers of as many pieces, the one of the longer first piece is taken.

    Args:
        length: The number of places to cover.
        piece: The piece that covers the places from a first up to a last, excluded, or None.

    Returns:
        The pieces, in their order, or None where they do not cover every place.
    """
    # The fewest pieces that cover the rest from each place on, or None.
    covers: list[list[str] | None] = [None] * length + [[]]
    for start in range(length - 1, -1, -1):
        for end in range(length, start, -1):
            found, rest = piece(start, end), covers[end]
            if found is None or rest is None:
                continue
            cover = covers[start]
            if cover is None or len(rest) + 1 < len(cover):
                covers[start] = [found, *rest]
    return covers[0]


class Vocabulary:
    """The terms a name is split into, of a profile, beyond the cuts `terms` makes.

    They are the terms found in its names and the terms its concepts are written as, which are
    never split, and are found whole across the cuts of `terms`.
    """

    def __init__(self, found: Collection[str], written: Collection[str]) -> None:
        """Takes the terms found in the names, and the terms the concepts are written as."""
        # Sorted, so that of two terms of the same pieces every run takes the same. One not in lower
        # case, as no term is, finds no name, and is warned of as any such abbreviation is.
        self._pieces = {tuple(terms(t)): t for t in sorted(written) if t.islower()}
        # Their pieces as well, as a term is not found any longer where one of them is split.
        self._kept = frozenset(written).union(*self._pieces)
        self._parts = frozenset(t for t in (*found, *written) if len(t) >= _SHORTEST)

    @classmethod
    def of(cls, profile: Profile) -> Self:
        """The vocabulary of `profile`: the terms of its names, and those of its concepts.

        Args:
            profile: The profile.

        Returns:
            The vocabulary, of the terms found in the names of the tables and columns, as the
            terms of its concepts split them, but those of digits, and of the terms its concepts
            are written as.
        """
        names = [table.name for table in profile.tables]
        names += [column.name for table in profile.tables for column in table.columns]
        written = {
            t for word, concept in profile.glossary.items() for t in written_as(word, concept)
        }
        # By its concepts alone, so that a piece of a term of theirs, `rd` of `3rd`, is no term.
        concepts_only = cls((), written)
        found = {term for name in names for term in concepts_only.split(name) if not term.isdigit()}
        return cls(found, written)

    def split(self, name: str) -> list[str]:
        """The terms of `name`: as `terms` cuts it, then split and joined by the vocabulary.

        Args:
            name: The original name, of a table or a column.

        Returns:
            The terms, in lower case, in their order: those written together split, and the pieces
            of a term a concept is written as joined into it.
        """
        return self._joined([part for term in terms(name) for part in self._split(term)])

    def _split(self, term: str) -> list[str]:
        """The parts of `term`, itself where the vocabulary does not cover it whole."""
        if term in self._kept or term.isdigit():
            return [term]

        def other_term(start: int, end: int) -> str | None:
            part = term[start:end]
            return part if part != term and part in self._parts else None

        parts = _fewest(len(term), other_term)
        if parts is None:
            return [term]
        return [found for part in parts for found in self._split(part)]

    def _joined(self, parts: list[str]) -> list[str]:
        """`parts`, those that are the pieces of a term a concept is written as joined into it."""

        def part_or_term(start: int, end: int) -> str | None:
            pieces = tuple(parts[start:end])
            return parts[start] if len(pieces) == 1 else self._pieces.get(pieces)

        # Each part covers its own place, so that a cover always is found.
        return _fewest(len(parts), part_or_term) or parts


def agrees(terms: tuple[Term, ...] | None, reading: tuple[str, ...] | None) -> bool:
    """Whether `reading` reads `terms`: as long as they are, each word a candidate of its term.

    Args:
        terms: The terms of a name, or None where it is not split.
        reading: The reading of the name, or None where it is not read.

    Returns:
        Whether both are there and of one length, and each word is a candidate of the term at its
        place.
    """
    if terms is None or reading is None or len(terms) != len(reading):
        return False
    return all(word in term.candidates for term, word in zip(terms, reading, strict=True))


class Glossary:
    """The concepts of a profile by the terms they are written as: the words of its names."""

    def __init__(self, concepts: Mapping[str, Concept]) -> None:
        """Takes the concepts, by their words."""
        self._concepts = concepts
        self._words: dict[str, list[str]] = {}
        for word, concept in concepts.items():
            for term in dict.fromkeys(written_as(word, concept)):
                self._words.setdefault(term, []).append(word)

    def concept(self, word: str) -> Concept | None:
        """The concept of `word`, or None where the glossary has none of it."""
        return self._concepts.get(word)

    def words(self, term: str) -> tuple[str, ...]:
        """The words of the concepts written as `term`, in the order of the glossary.

        Args:
            term: A term, in lower case.

        Returns:
            The words; none where the term is of no concept.
        """
        return tuple(self._words.get(term, ()))

    def terms(self, name: str, vocabulary: Vocabulary) -> tuple[Term, ...]:
        """The terms of `name`, as `vocabulary` splits it, each with its concepts.

        Args:
            name: The original name, of a table or a column.
            vocabulary: The vocabulary the name is split by.

        Returns:
            The terms, in their order, each with the words of the concepts written as it; none of
            a term of digits.
        """
        return tuple(
            Term(term, () if term.isdigit() else self.words(term))
            for term in vocabulary.split(name)
        )

    def harmonized(self, named: Table | Column) -> str | None:
        """The harmonized name of `named`: the words of its reading, in snake_case.

        Args:
            named: A table or a column, with the terms and the reading of its name.

        Returns:
            The name given by hand, where one is; else the harmonized name, without the words of
            the concepts omitted; None where its name has no reading that agrees with its terms, a
            word of it is of no concept of the glossary or of neither letters nor digits, or no
            word is left.
        """
        if named.name_given is not None:
            return named.name_given
        reading = named.reading
        if reading is None or not agrees(named.terms, reading):
            return None
        words = []
        for word in reading:
            if word.isdigit():
                words.append(word)
                continue
            concept = self._concepts.get(word)
            if concept is None:
                return None
            if concept.omitted:
                continue
            composed = snake_case(word)
            if not composed:
                return None
            words.append(composed)
        return "_".join(words) or None

    def collisions(self, table: Table) -> dict[str, tuple[str, ...]]:
        """Each harmonized name of two columns of `table` or more, with their original names.

        Args:
            table: The table, its columns with the terms and readings of their names.

        Returns:
            Each harmonized name that two columns or more have, in the order of the table, with
            the names of those columns, in their order.
        """
        found: dict[str, list[str]] = {}
        for column in table.columns:
            name = self.harmonized(column)
            if name is not None:
                found.setdefault(name, []).append(column.name)
        return {name: tuple(columns) for name, columns in found.items() if len(columns) > 1}
