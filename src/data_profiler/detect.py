"""Detection: semantic types, their sensitivity, and the detectors that recognise them.

A detector recognises one semantic type by a pattern, a regular expression every value of the type
matches whole - in a value, and on the whole table in SQL -, and, where the pattern does not say
enough, by a check of the value that matches it: the checksum of an IBAN, the number of a phone.
The pattern carries as much of the check as a pattern can, so that on the whole table, where the
pattern alone is tried, it lets few values pass that the check would refuse. A detector sees each
value as text, its spaces at either end cut, whatever the type of its column, so that every column
is checked. The patterns use what Python and the regular expressions of the databases share:
classes, repetitions, groups and alternatives, and no other escapes than of a character.
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum
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
    """Recognises one semantic type: by a pattern, and by a check of what the pattern matches.

    Attributes:
        pattern: A regular expression every value of the type matches whole, as Python and SQL
            read it; its text is what is sent to the database.
        check: Whether a value the pattern matches is of the type, where the pattern does not
            say enough; None where it does.
    """

    pattern: re.Pattern[str]
    check: Callable[[str], bool] | None = None

    def recognises(self, value: str) -> bool:
        """Whether `value` is of the type of the detector."""
        if not self.pattern.fullmatch(value):
            return False
        return self.check is None or self.check(value)


class SemanticType(Enum):
    """What the values of a column are: each type with its sensitivity and its detector.

    Its value is its name in the profile.
    """

    EMAIL = "email"
    PHONE = "phone"
    POSTAL_CODE = "postal-code"
    """A German postal code."""
    IBAN = "iban"
    CARD_NUMBER = "card-number"
    DATE = "date"
    """A date, with or without a time of day and a time zone, written as text."""

    @property
    def sensitivity(self) -> Sensitivity:
        """The rules the values of the type fall under."""
        match self:
            case SemanticType.EMAIL | SemanticType.PHONE | SemanticType.IBAN:
                return Sensitivity.PERSONAL
            case SemanticType.CARD_NUMBER:
                return Sensitivity.PAYMENT_CARD
            case SemanticType.POSTAL_CODE | SemanticType.DATE:
                return Sensitivity.NONE

    @property
    def detector(self) -> Detector:
        """The detector that recognises the type."""
        match self:
            case SemanticType.EMAIL:
                return _EMAIL
            case SemanticType.PHONE:
                return _PHONE
            case SemanticType.POSTAL_CODE:
                return _POSTAL_CODE
            case SemanticType.IBAN:
                return _IBAN
            case SemanticType.CARD_NUMBER:
                return _CARD_NUMBER
            case SemanticType.DATE:
                return _DATE


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


_EMAIL: Final = Detector(
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
)
# A phone number begins with its country, or with the zero of a call within the country; a dot is
# no separator of it, so that dates and decimals, which phonenumbers takes for numbers, are none.
_PHONE: Final = Detector(re.compile(r"(\+|\(?0)[0-9 ()/-]{5,24}"), _phone)
_POSTAL_CODE: Final = Detector(re.compile(r"(0[1-9]|[1-9][0-9])[0-9]{3}"))
# Two letters, two check digits, and up to 30 letters and digits, in groups of four or not.
_IBAN: Final = Detector(re.compile(r"[A-Z]{2}[0-9]{2}[A-Z0-9 ]{11,38}"), iban.is_valid)
# A card number begins with the digit of an issuer, 2 to 6, as its check digit alone would let a
# tenth of all numbers of its length pass.
_CARD_NUMBER: Final = Detector(re.compile(r"[2-6][0-9 -]{11,21}[0-9]"), _card_number)
_DATE: Final = Detector(
    re.compile(
        r"([0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
        r"|(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.[0-9]{4})"
        r"([ T]([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9](\.[0-9]+)?)?"
        r"( ?(Z|[+-][0-9]{2}:?[0-9]{2}|[A-Za-z][A-Za-z_/+-]*))?)?"
    ),
    _date,
)


def is_sensitive(text: str) -> bool:
    """Whether `text`, its spaces at either end cut, is of a semantic type of a sensitivity."""
    text = text.strip()
    return any(
        kind.sensitivity is not Sensitivity.NONE and kind.detector.recognises(text)
        for kind in SemanticType
    )


def detect(values: Sequence[object]) -> dict[SemanticType, float]:
    """The share of `values` each semantic type is recognised in, of the types one value is of.

    Args:
        values: The values of a column, as a sample holds them; None is a null, and not counted.

    Returns:
        The share of the values that are not null each type is recognised in, from 0 to 1, by
        type; a type no value is of is left out, and so is every type where all values are null.
    """
    texts = [str(value).strip() for value in values if value is not None]
    shares = {}
    for kind in SemanticType:
        recognised = sum(1 for text in texts if kind.detector.recognises(text))
        if recognised:
            shares[kind] = recognised / len(texts)
    return shares
