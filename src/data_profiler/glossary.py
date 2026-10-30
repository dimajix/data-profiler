"""The glossary: original names split into terms, and harmonized names composed from their words.

An original name - of a table or of a column - is split into its terms at everything that is no
letter and no digit, at a change from a lower case letter to an upper case one, before the last of
several upper case letters that a lower case one follows, and between letters and digits:
`CUST_CRT_DT` into `cust`, `crt` and `dt`, `custCrtDt` and `CUSTCrtDt` alike, `addr2` into `addr`
and `2`. A term is in lower case, so that `CUST` and `cust` are one. The glossary of a profile
gives each term the word it stands for, once for the whole schema; a harmonized name is composed of
the words of the terms of the original name, each split as a name is, in `snake_case`, and a term
of digits stands for itself.
"""

import re
import unicodedata
from collections.abc import Mapping
from typing import Final

from data_profiler.profile import Profile

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
        Each term that needs a word, in the order it first appears, with the names it appears in,
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


def harmonized(name: str, glossary: Mapping[str, str]) -> str | None:
    """The harmonized name of `name`: the words of its terms, in snake_case.

    Args:
        name: The original name, of a table or a column.
        glossary: The word of each term.

    Returns:
        The harmonized name, or None while a term of the name has no word - none at all, or one
        of neither letters nor digits -, or the name no term.
    """
    words = []
    for term in terms(name):
        word = term if term.isdigit() else "_".join(terms(glossary.get(term, "")))
        if not word:
            return None
        words.append(word)
    return "_".join(words) or None
