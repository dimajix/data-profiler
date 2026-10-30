"""Rows of test data whose columns have the statistics of a profile.

The values of a column are drawn from a pool of as many distinct values as its statistics count,
each of them used at least once, and its nulls are spread over the rows at random. What the values
are follows from the type of the column: texts are letters of the counted lengths, and where the
column has a match, values of its first semantic type, of those lengths, which its detector
recognises - all of them, whatever the shares of the match.
"""

import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from random import Random
from string import ascii_lowercase, digits
from typing import Final

from stdnum.iban import calc_check_digits
from stdnum.luhn import calc_check_digit

from data_profiler.detect import SemanticType
from data_profiler.profile import Column, Lengths, Table
from simulation import SimulationError

# The first day of the dates and times generated, its first moment, and how many days they span.
_EPOCH: Final = date(2000, 1, 1)
_START: Final = datetime.combine(_EPOCH, datetime.min.time())
_DAYS: Final = 9800

# How often a value is drawn for each one the pool still lacks, and a text of a semantic type for
# each value drawn, before it is given up as impossible.
_ATTEMPTS: Final = 50

# The ranges of the integer types, as far as test data needs them: positive, as keys are.
_INTEGERS: Final = {"smallint": 2**15 - 1, "integer": 2**31 - 1, "bigint": 10**12}

# How phone numbers begin: within Germany, by the zero of a call within it, or from abroad.
_PHONES: Final = ("030 ", "040 ", "089 ", "+49 30 ")

# The forms of a date as text, by their lengths, as `datetime.strftime` writes them.
_DATES: Final = {
    10: ("%Y-%m-%d", "%d.%m.%Y"),
    16: ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"),
    19: ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"),
}


def rows(table: Table, random: Random) -> list[tuple[object, ...]]:
    """The rows of `table`, each of its columns with its nulls, distinct values and lengths.

    Args:
        table: The table, with the statistics of its columns.
        random: Where the values are drawn from; the same seed gives the same rows.

    Returns:
        The rows, each a tuple of the values of the columns in their order; None is a null.

    Raises:
        SimulationError: A column has a type that is not generated, or statistics that no values
            can have.
    """
    return list(zip(*(_values(table, column, random) for column in table.columns), strict=True))


def _values(table: Table, column: Column, random: Random) -> list[object]:
    """The values of `column`, one per row of `table`, in random order."""
    statistics = column.statistics
    present = table.rows - statistics.nulls
    if present < 0 or statistics.distinct > present or (present > 0 and statistics.distinct == 0):
        raise SimulationError(
            f"{table.name}.{column.name}: {statistics.distinct} distinct values and "
            f"{statistics.nulls} nulls do not fit {table.rows} rows"
        )
    pool = _pool(table, column, random)
    values: list[object] = [*pool, *random.choices(pool, k=present - len(pool))]
    values += [None] * statistics.nulls
    random.shuffle(values)
    return values


def _pool(table: Table, column: Column, random: Random) -> list[object]:
    """As many distinct values of the type of `column` as its statistics count."""
    count = column.statistics.distinct
    match = re.fullmatch(r"(\w+)(?:\((\d+)(?:,\s*(\d+))?\))?", column.type)
    kind, first, second = match.groups() if match else (column.type, None, None)
    if count == 0:
        return []
    try:
        if kind in _INTEGERS:
            return list(random.sample(range(1, _INTEGERS[kind]), count))
        if kind == "decimal" and first is not None:
            scale = int(second or 0)
            numbers = random.sample(range(10 ** int(first)), count)
            return [Decimal(number).scaleb(-scale) for number in numbers]
        if kind == "date":
            return [_EPOCH + timedelta(days=day) for day in random.sample(range(_DAYS), count)]
        if kind == "timestamp":
            seconds = random.sample(range(_DAYS * 86400), count)
            return [_START + timedelta(seconds=second) for second in seconds]
        if kind == "boolean":
            return list(random.sample([False, True], count))
    except ValueError as error:
        raise SimulationError(
            f"{table.name}.{column.name}: a {column.type} has fewer than {count} distinct values"
        ) from error
    if kind == "double":
        return _distinct(table, column, lambda: round(random.uniform(0, 10**6), 4))
    if kind == "varchar":
        return _texts(table, column, random)
    raise SimulationError(f"{table.name}.{column.name}: the type {column.type} is not generated")


def _texts(table: Table, column: Column, random: Random) -> list[object]:
    """The distinct texts of `column`, of its lengths: its shortest and its longest among them.

    They are of the first semantic type of the column where it has a match, else letters.
    """
    lengths = column.statistics.lengths
    if lengths is None:
        raise SimulationError(f"{table.name}.{column.name}: a text column without its lengths")
    wanted = iter([lengths.shortest, lengths.longest])
    kind = column.matches[0].type if column.matches else None

    def draw() -> str:
        given = next(wanted, None)
        if kind is None:
            return _letters(_length(given, lengths, random), random)
        # Each try of a length of its own, as not every length between the shortest and the
        # longest is one of a value of the type.
        for _ in range(_ATTEMPTS):
            length = _length(given, lengths, random)
            text = _typed(kind, length, random)
            if len(text) == length and kind.detector.recognises(text):
                return text
        within = given if given is not None else f"{lengths.shortest} to {lengths.longest}"
        raise SimulationError(
            f"{table.name}.{column.name}: no {kind.value} of {within} characters can be made"
        )

    return _distinct(table, column, draw)


def _length(given: int | None, lengths: Lengths, random: Random) -> int:
    """`given`, or where it is None a length from the shortest to the longest, at random."""
    return given if given is not None else random.randint(lengths.shortest, lengths.longest)


def _typed(kind: SemanticType, length: int, random: Random) -> str:
    """A text that may be of `kind` and of `length` characters, which the caller is to tell.

    It is a `match` over the semantic types, as their sensitivity and their detector are, so that
    mypy finds it incomplete when a type is added; making test data is no concern of the tool.
    """
    match kind:
        case SemanticType.EMAIL:
            domain = max(1, (length - 4) // 3)
            return f"{_letters(length - domain - 4, random)}@{_letters(domain, random)}.de"
        case SemanticType.PHONE:
            prefix = random.choice(_PHONES)
            return prefix + _digits(length - len(prefix), random)
        case SemanticType.POSTAL_CODE:
            return _digits(length, random)
        case SemanticType.IBAN:
            # A German IBAN: the bank of eight digits and the account of ten; in groups of four,
            # it is five characters longer.
            number = "DE00" + _digits(18, random)
            number = number[:2] + calc_check_digits(number) + number[4:]
            grouped = " ".join(number[start : start + 4] for start in range(0, len(number), 4))
            return grouped if length == len(grouped) else number
        case SemanticType.CARD_NUMBER:
            number = random.choice("45") + _digits(length - 2, random)
            return number + calc_check_digit(number)
        case SemanticType.DATE:
            moment = _START + timedelta(seconds=random.randrange(_DAYS * 86400))
            return moment.strftime(random.choice(_DATES.get(length, ("",))))


def _letters(length: int, random: Random) -> str:
    """A text of `length` lower case letters."""
    return "".join(random.choices(ascii_lowercase, k=length))


def _digits(length: int, random: Random) -> str:
    """A text of `length` digits."""
    return "".join(random.choices(digits, k=length))


def _distinct(table: Table, column: Column, draw: Callable[[], object]) -> list[object]:
    """As many distinct values drawn by `draw` as the statistics of `column` count."""
    count = column.statistics.distinct
    pool: dict[object, None] = {}
    for _ in range(_ATTEMPTS * count):
        pool[draw()] = None
        if len(pool) == count:
            return list(pool)
    raise SimulationError(f"{table.name}.{column.name}: {count} distinct values cannot be drawn")
