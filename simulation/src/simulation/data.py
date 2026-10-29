"""Rows of test data whose columns have the statistics of a profile.

The values of a column are drawn from a pool of as many distinct values as its statistics count,
each of them used at least once, and its nulls are spread over the rows at random. What the values
are follows from the type of the column alone - texts are letters of the counted lengths -, until
the profile knows the semantic types of its columns.
"""

import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from random import Random
from string import ascii_lowercase
from typing import Final

from data_profiler.profile import Column, Table
from simulation import SimulationError

# The first day of the dates and times generated, and how many days they span.
_EPOCH: Final = date(2000, 1, 1)
_DAYS: Final = 9800

# How often a value is drawn for each one the pool still lacks, before it is given up as impossible.
_ATTEMPTS: Final = 50

# The ranges of the integer types, as far as test data needs them: positive, as keys are.
_INTEGERS: Final = {"smallint": 2**15 - 1, "integer": 2**31 - 1, "bigint": 10**12}


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
            start = datetime.combine(_EPOCH, datetime.min.time())
            seconds = random.sample(range(_DAYS * 86400), count)
            return [start + timedelta(seconds=second) for second in seconds]
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
    """The distinct texts of `column`, of its lengths: its shortest and its longest among them."""
    lengths = column.statistics.lengths
    if lengths is None:
        raise SimulationError(f"{table.name}.{column.name}: a text column without its lengths")
    wanted = iter([lengths.shortest, lengths.longest])

    def draw() -> str:
        length = next(wanted, None)
        if length is None:
            length = random.randint(lengths.shortest, lengths.longest)
        return "".join(random.choices(ascii_lowercase, k=length))

    return _distinct(table, column, draw)


def _distinct(table: Table, column: Column, draw: Callable[[], object]) -> list[object]:
    """As many distinct values drawn by `draw` as the statistics of `column` count."""
    count = column.statistics.distinct
    pool: dict[object, None] = {}
    for _ in range(_ATTEMPTS * count):
        pool[draw()] = None
        if len(pool) == count:
            return list(pool)
    raise SimulationError(f"{table.name}.{column.name}: {count} distinct values cannot be drawn")
