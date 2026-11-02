"""Detection: semantic types, their sensitivity, and the detectors that recognise them.

A detector recognises one semantic type by a pattern, a regular expression every value of the type
matches whole - in a value, and on the whole table in SQL -, and, where the pattern does not say
enough, by a check of the value that matches it: the checksum of an IBAN, the number of a phone.
The pattern carries as much of the check as a pattern can, so that on the whole table, where the
pattern alone is tried, it lets few values pass that the check would refuse. Where a value does not
say enough even with its check, a condition of the column judges the values of a sample together.
A detector names the share of the values of a sample it has to recognise for its type to be a match
of their column, its threshold: half of them, unless it names another. A detector sees each
value as text, its spaces at either end cut, whatever the type of its column, so that every column
is checked. The patterns use what Python and the regular expressions of the databases share:
classes, repetitions, groups and alternatives, and no other escapes than of a character.

The types of the tool are the constants below; a project gives types of its own, each by its name,
its sensitivity and a pattern alone, which a value is checked for beside those of the tool.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum
from re import PatternError
from typing import Final

from phonenumbers import NumberParseException, is_valid_number, parse
from stdnum import iban, luhn


class Sensitivity(Enum):
    """The rules the values of a semantic type fall under."""

    NONE = "none"
    PERSONAL = "personal"
    """Personal data, under the GDPR."""
    PAYMENT_CARD = "payment-card"
    """Payment card data, under the PCI DSS."""


@dataclass(frozen=True)
class Detector:
    """Recognises one semantic type: by a pattern, a check of a value and a condition of its column.

    Attributes:
        pattern: A regular expression every value of the type matches whole, as Python and SQL
            read it; its text is what is sent to the database.
        check: Whether a value the pattern matches is of the type, where the pattern does not
            say enough; None where it does.
        column: Whether the texts of a column, together, are of the type, where no value says it
            alone; None where each value does. It is given all texts of the column, and those of
            them the detector recognises, one or more: it is asked only where there is one. It is
            judged on a sample, never on the table.
        threshold: The share of the values of a sample the detector has to recognise for its
            type to be a match of their column; half of them unless another is given, a low
            share, as more hypotheses are better than fewer.
    """

    pattern: re.Pattern[str]
    check: Callable[[str], bool] | None = None
    column: Callable[[Sequence[str], Sequence[str]], bool] | None = None
    threshold: float = 0.5

    def recognises(self, value: str) -> bool:
        """Whether `value` is of the type of the detector."""
        if not self.pattern.fullmatch(value):
            return False
        return self.check is None or self.check(value)

    def share(self, texts: Sequence[str]) -> float:
        """The share of `texts` of the type, from 0 to 1; 0 where the texts together are not."""
        recognised = [text for text in texts if self.recognises(text)]
        if not recognised or (self.column is not None and not self.column(texts, recognised)):
            return 0.0
        return len(recognised) / len(texts)


# The region of a phone number written without its country code.
_REGION: Final = "DE"


def _phone(value: str) -> bool:
    """Whether `value` is a phone number that can be dialled, of Germany if it names no country."""
    try:
        return is_valid_number(parse(value, _REGION))
    except NumberParseException:
        return False


def _card_number(value: str) -> bool:
    """Whether the check digit of the number of a payment card `value` is right."""
    return luhn.is_valid(re.sub(r"[ -]", "", value))


def _date(value: str) -> bool:
    """Whether the day of `value`, a date the pattern of a date matches, is in the calendar."""
    if value[4] == "-":
        year, month, day = value[0:4], value[5:7], value[8:10]
    else:
        day, month, year = value[0:2], value[3:5], value[6:10]
    try:
        date(int(year), int(month), int(day))
    except ValueError:
        return False
    return True


# A value of words: two words or more, one of them after the first beginning in lower case, as free
# text has many of; the classes other than of a space let a word hold a line break, which `.` does
# not match.
_OF_WORDS: Final = re.compile(r"[^ ]+( +[^ ]+)* +[a-zäöüß][^ ]*( +[^ ]+)*")

# A word in lower case, as the pattern of a value of words takes it: one that begins with a letter
# of its class.
_LOWER: Final = re.compile("[a-zäöüß]")

# Of free text: the share of the words after the first of their value that are in lower case, the
# share of letters among the characters other than spaces, and the share of distinct values among
# the values of words, each at least.
_LOWER_CASE: Final = 0.3
_LETTERS: Final = 0.7
_DISTINCT: Final = 0.5


def _free_text(texts: Sequence[str], of_words: Sequence[str]) -> bool:
    """Whether `texts`, of which `of_words` are values of words, are free text.

    The words in lower case tell prose from names, addresses and products, of capitals mostly, in
    German as in English; the letters tell it from codes and numbers; and the values of words that
    are distinct tell it from categories of several words, whatever short values repeat beside
    them.
    """
    # Words are what stands between spaces, as the pattern of a value of words takes them.
    words = [word for text in texts for word in text.split(" ")[1:] if word]
    lower = sum(1 for word in words if _LOWER.match(word))
    characters = [character for text in texts for character in text if character != " "]
    letters = sum(1 for character in characters if character.isalpha())
    return (
        lower >= _LOWER_CASE * len(words)
        and letters >= _LETTERS * len(characters)
        and len(set(of_words)) >= _DISTINCT * len(of_words)
    )


@dataclass(frozen=True)
class SemanticType:
    """What the values of a column are: a name, the rules its values fall under, and its detector.

    Attributes:
        name: The name of the type in the profile.
        sensitivity: The rules the values of the type fall under.
        detector: The detector that recognises the type.
    """

    name: str
    sensitivity: Sensitivity
    detector: Detector


EMAIL: Final = SemanticType(
    "email",
    Sensitivity.PERSONAL,
    Detector(re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
)
# A phone number begins with its country, or with the zero of a call within the country; a dot is
# no separator of it, so that dates and decimals, which phonenumbers takes for numbers, are none.
PHONE: Final = SemanticType(
    "phone", Sensitivity.PERSONAL, Detector(re.compile(r"(\+|\(?0)[0-9 ()/-]{5,24}"), _phone)
)
POSTAL_CODE: Final = SemanticType(
    "postal-code", Sensitivity.NONE, Detector(re.compile(r"(0[1-9]|[1-9][0-9])[0-9]{3}"))
)
"""A German postal code."""
# Two letters, two check digits, and up to 30 letters and digits, in groups of four or not.
IBAN: Final = SemanticType(
    "iban",
    Sensitivity.PERSONAL,
    Detector(re.compile(r"[A-Z]{2}[0-9]{2}[A-Z0-9 ]{11,38}"), iban.is_valid),
)
# A card number begins with the digit of an issuer, 2 to 6, as its check digit alone would let a
# tenth of all numbers of its length pass.
CARD_NUMBER: Final = SemanticType(
    "card-number",
    Sensitivity.PAYMENT_CARD,
    Detector(re.compile(r"[2-6][0-9 -]{11,21}[0-9]"), _card_number),
)
DATE: Final = SemanticType(
    "date",
    Sensitivity.NONE,
    Detector(
        re.compile(
            r"([0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
            r"|(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.[0-9]{4})"
            r"([ T]([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9](\.[0-9]+)?)?"
            r"( ?(Z|[+-][0-9]{2}:?[0-9]{2}|[A-Za-z][A-Za-z_/+-]*))?)?"
        ),
        _date,
    ),
)
"""A date, with or without a time of day and a time zone, written as text."""
# 32 hexadecimal digits in groups of 8, 4, 4, 4 and 12; their version and variant are not checked,
# so that a UUID of any kind is recognised, as the groups alone say enough.
UUID: Final = SemanticType(
    "uuid",
    Sensitivity.NONE,
    Detector(re.compile(r"[0-9A-Fa-f]{8}(-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}")),
)
"""A UUID, written as text in the form of RFC 9562."""
# Values of words, of a column of free text; a fifth of the values is enough, as a column of
# comments holds many short ones too.
FREE_TEXT: Final = SemanticType(
    "free-text", Sensitivity.NONE, Detector(_OF_WORDS, column=_free_text, threshold=0.2)
)
"""Free text, such as a comment, a note or a description, of words and sentences."""

BUILT_IN: Final = (EMAIL, PHONE, POSTAL_CODE, IBAN, CARD_NUMBER, DATE, UUID, FREE_TEXT)
"""The semantic types of the tool."""

# The name of a semantic type of a project, of lower case letters, digits and `-`, as the names of
# the types of the tool are.
_NAME: Final = re.compile(r"[a-z0-9][a-z0-9-]*")


class SemanticTypeError(Exception):
    """A semantic type of a project that cannot be made: its name, and what is wrong with it."""


def project_type(name: str, sensitivity: Sensitivity, pattern: str) -> SemanticType:
    """A semantic type of a project, recognised by its pattern alone.

    Args:
        name: The name of the type.
        sensitivity: The rules the values of the type fall under.
        pattern: The regular expression every value of the type matches whole.

    Returns:
        The semantic type.

    Raises:
        SemanticTypeError: The name is one of a type of the tool, or of other characters than
            lower case letters, digits and `-`, or the pattern is no regular expression of Python.
    """
    if not _NAME.fullmatch(name):
        raise SemanticTypeError(
            f"{name!r} is named other than in lower case letters, digits and '-', beginning with"
            " a letter or a digit"
        )
    if semantic_type(name, ()) is not None:
        raise SemanticTypeError(f"{name} is a semantic type of the tool")
    try:
        compiled = re.compile(pattern)
    except PatternError as error:
        raise SemanticTypeError(
            f"the pattern of {name} is no regular expression: {error}"
        ) from error
    return SemanticType(name, sensitivity, Detector(compiled))


def all_types(types: Sequence[SemanticType]) -> tuple[SemanticType, ...]:
    """The semantic types the values of a project are checked for: the tool's, then `types`."""
    return (*BUILT_IN, *types)


def semantic_type(name: str, types: Sequence[SemanticType]) -> SemanticType | None:
    """The semantic type named `name`, of the tool or of `types`, a project's; None if none is."""
    return next((kind for kind in all_types(types) if kind.name == name), None)


def is_sensitive(text: str, types: Sequence[SemanticType]) -> bool:
    """Whether `text`, its spaces at either end cut, is of a type of a sensitivity.

    Args:
        text: The text.
        types: The semantic types of the project, checked beside those of the tool.

    Returns:
        Whether a type of the tool or of the project of a sensitivity recognises the text.
    """
    text = text.strip()
    return any(
        kind.sensitivity is not Sensitivity.NONE and kind.detector.recognises(text)
        for kind in all_types(types)
    )


def detect(values: Sequence[object], types: Sequence[SemanticType]) -> dict[SemanticType, float]:
    """The share of `values` each semantic type is recognised in, of the types they are a match of.

    Args:
        values: The values of a column, as a sample holds them; None is a null, and not counted.
        types: The semantic types of the project, checked beside those of the tool.

    Returns:
        The share of the values that are not null each type is recognised in, from 0 to 1, by
        type, of the types whose share reaches the threshold of their detector; every other type
        is left out, and so is every type where all values are null.
    """
    texts = [str(value).strip() for value in values if value is not None]
    shares = {kind: kind.detector.share(texts) for kind in all_types(types)}
    return {kind: share for kind, share in shares.items() if share >= kind.detector.threshold}
