"""Rows of test data whose columns have the statistics of a profile.

The values of a column are drawn from a pool of as many distinct values as its statistics count,
each of them used at least once, and its nulls and sentinels are spread over the rows at random:
the rows of a column are taken in an order of their own, its nulls and sentinels in the first of
them. The columns of a group share their order, so that they are filled in the same rows as far as
their nulls and sentinels allow: the column of more of them is filled within the rows of the column
of fewer. A column that follows from another, by a column dependency, is made of the values of the
other: its distinct values, as they first come, take the values of its pool in their order, again
from the first where they are more, so that the columns that follow from one follow from each other
where their pools are as large; it is null where the other is not filled. A table of a discriminator
holds the values of its column in as many rows as the profile counts each, the rows of each entity
those of its values, and each column is filled in as many rows of each entity as the entity counts,
its nulls and sentinels in the others; the discriminator is a column of text. Of a key of two
columns, the column of fewer distinct values is numbered within the other: its values, in their
order, by the place of each row among the rows of the same value of the other, which holds each of
its values in as many rows at most as the first has values, and one of them in as many, so that the
pair is unique and each column has its distinct values.
Each column draws its values from a random of its own, made of the seed and its name and that of its
table, its pool first, so that the values of a key are drawn again the same for a column of a
reference to it, of whatever table: the column holds as many of them as its distinct values count,
less those outside of the key, in as many rows as its coverage says; those outside, of a column of
whole numbers alone, are above the largest of the key, each in one row, whatever range the column
has itself. A reference of unmistakable values, of no coverage, holds values of the key alone.
What the values are follows from the type of the column: texts are letters of the counted lengths,
and where the column has a match, values of its first semantic type, of those lengths, which its
detector recognises - all of them, whatever the shares of the match -, and which meet the condition
of its column together, where the detector has one; a column of lists holds lists of the values of
its items, separated by its separator, drawn as the texts of a column of their statistics and
matches are, digits where they have no match; whole numbers of a range lie within it, its ends among
them, in their order, all of it where they are as many, as a key numbered from one is. Values are
made of the semantic types of the tool alone, not of those of a project. The sentinels of a column
are made as many times as the profile counts each: a text as it is written, a day or a moment of the
day it names in the form of ISO 8601.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from random import Random
from string import ascii_lowercase, digits
from typing import Final

from stdnum.iban import calc_check_digits
from stdnum.luhn import calc_check_digit

from data_profiler.currencies import CODES, NAMES, NUMBERS
from data_profiler.detect import (
    CARD_NUMBER,
    CURRENCY_CODE,
    CURRENCY_NAME,
    CURRENCY_NUMBER,
    DATE,
    EMAIL,
    FREE_TEXT,
    IBAN,
    PHONE,
    POSTAL_CODE,
    TRUE_FALSE,
    UUID,
    YES_NO,
    ZERO_ONE,
    SemanticType,
    cases,
    is_filled,
    is_list,
)
from data_profiler.profile import (
    Column,
    Discriminator,
    Lengths,
    Match,
    Profile,
    Reference,
    Table,
)
from simulation import SimulationError

# The first day of the dates and times generated, its first moment, and how many days they span.
_EPOCH: Final = date(2000, 1, 1)
_START: Final = datetime.combine(_EPOCH, datetime.min.time())
_DAYS: Final = 9800

# How often a value is drawn for each one the pool still lacks, and a text of a semantic type for
# each value drawn, before it is given up as impossible.
_ATTEMPTS: Final = 50

# The chance that a list takes one more value where the rest could be its last.
_LONGER: Final = 0.5

# The ranges of the integer types, as far as test data needs them: positive, as keys are.
_INTEGERS: Final = {"smallint": 2**15 - 1, "integer": 2**31 - 1, "bigint": 10**12}

# How phone numbers begin: within Germany, by the zero of a call within it, or from abroad.
_PHONES: Final = ("030 ", "040 ", "089 ", "+49 30 ")

# The words of a comment: the first of its words, and those after it, most of them in lower case.
_FIRST: Final = ("Kunde", "Rechnung", "Lieferung", "Rückruf", "Termin", "Zahlung", "Bitte")
_WORDS: Final = (
    *("bittet", "um", "am", "an", "die", "der", "wegen", "nicht", "noch", "ist", "wurde", "und"),
    *("später", "erhalten", "geändert", "geklärt", "offen", "gemäß", "telefonisch", "per"),
    *("Montag", "Freitag", "Adresse", "Ware", "Ersatz", "Mail"),
)

# The forms of a date as text, by their lengths, as `datetime.strftime` writes them.
_DATES: Final = {
    10: ("%Y-%m-%d", "%d.%m.%Y"),
    16: ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"),
    19: ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"),
}


def rows(table: Table, profile: Profile, seed: int) -> list[tuple[object, ...]]:
    """The rows of `table`, each column with its nulls, sentinels, distinct values and lengths.

    The columns of each of its column groups are filled in the same rows, as far as their nulls and
    sentinels allow, and in as many rows of each entity of its discriminator as the entity counts;
    of each of its keys of two columns, the column of fewer values is numbered within the other;
    each column of a reference holds values of the key it refers to, and as many rows of values
    outside of it as its coverage leaves; each column that follows from another, by a column
    dependency, is made of the values of the other.

    Args:
        table: The table, with the statistics of its columns.
        profile: The profile of the tables its references refer to, `table` among them where it
            refers to itself.
        seed: Where the values are drawn from; the same seed gives the same rows, and the same
            values of a key to the tables that refer to it.

    Returns:
        The rows, each a tuple of the values of the columns in their order; None is a null.

    Raises:
        SimulationError: A column has a type that is not generated, or statistics that no values
            can have, or the entities of its discriminator rows that its column or the statistics
            of a column do not have, or a column of a key of two columns nulls or sentinels, or
            values too few for the rows, or a reference refers to a table `profile` does not
            have, to a column it does not have, or to one that refers itself, is of a coverage
            that no values of the column and the key can have, or of a column numbered within
            another or of the discriminator, or a column that follows from another is a key, a
            reference, of a column group or of a table of entities, follows from itself, or cannot
            follow from the other, as `_following` says.
    """
    random = Random(f"{seed}/{table.name}")
    # Of each key of two columns, the column numbered within the other, and the rows each value of
    # the other is in at most.
    numbered = _numbered(table)
    most = {other: table.column(name).statistics.distinct for name, other in numbered.items()}
    references = {reference.column: reference for reference in table.references}
    discriminator = table.discriminator
    told = set() if discriminator is None else {discriminator.column}
    unreferring = next((name for name in references if name in numbered or name in told), None)
    if unreferring is not None:
        raise SimulationError(
            f"{table.name}.{unreferring}: a column numbered or of a discriminator refers"
        )
    determined = _determined(table)
    shared = {}
    for found in table.column_groups:
        order = random.sample(range(table.rows), table.rows)
        shared.update(dict.fromkeys(found.columns, order))
    kinds = [] if discriminator is None else _kinds(table, discriminator, random)
    columns: dict[str, list[object]] = {}
    made = (c for c in table.columns if c.name not in numbered and c.name not in determined)
    for column in made:
        order = shared.get(column.name) or random.sample(range(table.rows), table.rows)
        own = _own(table, column, seed)
        if discriminator is not None and column.name == discriminator.column:
            columns[column.name] = _discriminated(table, column, kinds, random)
            continue
        if discriminator is not None:
            order = _within(table, column, discriminator, order, kinds)
        reference = references.get(column.name)
        pool = (
            _Pool(_pool(table, column, own))
            if reference is None
            else _referred(table, reference, profile, seed, own)
        )
        columns[column.name] = _values(table, column, order, own, pool, most.get(column.name))
    for name, other in numbered.items():
        column = table.column(name)
        own = _own(table, column, seed)
        columns[name] = _within_other(_pool(table, column, own), columns[other])
    # Each column after the one it follows from, which may follow from another itself.
    waiting = dict(determined)
    while waiting:
        ready = [name for name, determinant in waiting.items() if determinant in columns]
        if not ready:
            raise SimulationError(f"{table.name}.{next(iter(waiting))}: follows from itself")
        for name in ready:
            determinant = table.column(waiting.pop(name))
            values = columns[determinant.name]
            columns[name] = _following(table, table.column(name), determinant, values, seed)
    return list(zip(*(columns[column.name] for column in table.columns), strict=True))


@dataclass(frozen=True)
class _Pool:
    """The distinct values of a column: those in the rows they fill, and those in one row each.

    Attributes:
        filling: The values in the rows they fill, each in one at least.
        once: The values in one row each: of a column of a reference, those outside of its key.
    """

    filling: list[object]
    once: list[object] = field(default_factory=list)


def _own(table: Table, column: Column, seed: int) -> Random:
    """Where the values of `column` of `table` are drawn from, its pool first, by `seed`.

    A column draws from a random of its own, so that the values of a key are drawn again the same
    for a column that refers to it, of whatever table.
    """
    return Random(f"{seed}/{table.name}/{column.name}")


def _referred(
    table: Table, reference: Reference, profile: Profile, seed: int, random: Random
) -> _Pool:
    """Of the column of `reference`, the distinct values of its key it holds, and those outside.

    The values of the key are drawn again as it draws them; those outside, as many as the rows its
    coverage leaves, are whole numbers above the largest of the key, each in one row.

    Raises:
        SimulationError: The reference refers to a table `profile` does not have, to a column it
            does not have, or to one that refers itself, or of a coverage that no values of the
            column and the key can have, or of values outside of the key that cannot be made.
    """
    column = table.column(reference.column)
    where = f"{table.name}.{column.name}"
    try:
        referred = profile.table(reference.table)
        key = referred.column(reference.key)
    except KeyError as error:
        raise SimulationError(
            f"{where}: refers to {reference.table}.{reference.key}, not made"
        ) from error
    if any(found.column == key.name for found in referred.references):
        raise SimulationError(f"{where}: refers to a key that refers itself")
    values = _pool(referred, key, _own(referred, key, seed))
    statistics = column.statistics
    present = table.rows - statistics.nulls - statistics.sentinel_rows
    outside = 0 if reference.coverage is None else round((1 - reference.coverage) * present)
    held = statistics.distinct - outside
    if not 0 < held <= len(values) or held > present - outside:
        raise SimulationError(
            f"{where}: {statistics.distinct} distinct values of {present} rows cannot cover"
            f" {reference.coverage} of a key of {len(values)}"
        )
    if not outside:
        return _Pool(random.sample(values, held))
    kind, _ = _type(column)
    numbers = [value for value in values if isinstance(value, int)]
    if kind not in _INTEGERS or len(numbers) != len(values):
        raise SimulationError(f"{where}: no {column.type} outside of a key of {key.type} is made")
    beyond = max(numbers) + 1
    if beyond + outside > _INTEGERS[kind]:
        raise SimulationError(f"{where}: {outside} values above the key exceed a {column.type}")
    return _Pool(random.sample(values, held), list(range(beyond, beyond + outside)))


def _numbered(table: Table) -> dict[str, str]:
    """Of each key of two columns of `table`, the column of fewer distinct values, and the other.

    Raises:
        SimulationError: A column of a key of two columns has nulls or sentinels.
    """
    numbered = {}
    for key in table.keys:
        if len(key) == 2:
            pair = [table.column(name) for name in key]
            for column in pair:
                if column.statistics.nulls or column.statistics.sentinels:
                    raise SimulationError(
                        f"{table.name}.{column.name}: a column of a key has nulls or sentinels"
                    )
            fewer, other = sorted(pair, key=lambda column: column.statistics.distinct)
            numbered[fewer.name] = other.name
    return numbered


def _determined(table: Table) -> dict[str, str]:
    """Of each column of `table` that follows from another, by a column dependency, the other.

    A column that follows from several follows from the first of them.

    Raises:
        SimulationError: A column that follows from another is a key, a reference or the
            discriminator, of a column group, or of a table of entities, which are not made.
    """
    determined: dict[str, str] = {}
    for dependency in table.column_dependencies:
        first, *others = (*dependency.determinants, *dependency.dependents)
        for name in others:
            determined.setdefault(name, first)
    if determined and table.discriminator is not None:
        raise SimulationError(f"{table.name}: a column follows from another in a table of entities")
    keys = {name for key in table.keys for name in key}
    references = {reference.column for reference in table.references}
    grouped = {name for group in table.column_groups for name in group.columns}
    made = next((name for name in determined if name in keys | references | grouped), None)
    if made is not None:
        raise SimulationError(f"{table.name}.{made}: a key, reference or grouped column follows")
    return determined


def _following(
    table: Table, column: Column, determinant: Column, values: list[object], seed: int
) -> list[object]:
    """The values of `column`, which follow from `values` of `determinant`, one per row.

    The distinct values of the determinant, as they first come, take the values of the pool of the
    column in their order, again from its first where they are more, so that the columns that
    follow from one determinant follow from each other where their pools are as large; the column
    is null where the determinant is not filled.

    Raises:
        SimulationError: The column has sentinels, other nulls than the rows the determinant is not
            filled in, or more distinct values than it.
    """
    filled = [is_filled(value, determinant.left_aside) for value in values]
    statistics = column.statistics
    places: dict[object, int] = {}
    for value, taken in zip(values, filled, strict=True):
        if taken:
            places.setdefault(value, len(places))
    if (
        statistics.sentinels
        or statistics.nulls != filled.count(False)
        or not 0 < statistics.distinct <= len(places)
    ):
        raise SimulationError(
            f"{table.name}.{column.name}: does not follow from {determinant.name}, of its nulls,"
            f" sentinels and distinct values"
        )
    pool = _pool(table, column, _own(table, column, seed))
    return [
        pool[places[value] % len(pool)] if taken else None
        for value, taken in zip(values, filled, strict=True)
    ]


def _within_other(pool: list[object], other: list[object]) -> list[object]:
    """Of each row of `other`, the value of `pool` at the place of the row in those of its value."""
    seen: dict[object, int] = {}
    values = []
    for value in other:
        place = seen.get(value, 0)
        seen[value] = place + 1
        values.append(pool[place])
    return values


def _kinds(
    table: Table, discriminator: Discriminator, random: Random
) -> list[tuple[int, str] | None]:
    """Of each row of `table`, its entity, by its place, and its value; None of a row of none."""
    (column,) = (column for column in table.columns if column.name == discriminator.column)
    counted = {value.value: value.rows for value in column.values}
    kinds: list[tuple[int, str] | None] = []
    for index, entity in enumerate(discriminator.entities):
        held = all(value in counted for value in entity.values)
        if not held or sum(counted[value] for value in entity.values) != entity.rows:
            raise SimulationError(
                f"{table.name}.{column.name}: the rows of the values of an entity are not its own"
            )
        for value in entity.values:
            kinds += [(index, value)] * counted[value]
    if len(kinds) > table.rows:
        raise SimulationError(f"{table.name}: its entities have more rows than the table")
    kinds += [None] * (table.rows - len(kinds))
    random.shuffle(kinds)
    return kinds


def _discriminated(
    table: Table, column: Column, kinds: list[tuple[int, str] | None], random: Random
) -> list[object]:
    """The values of the discriminator `column`: of each row its value, else a null or sentinel."""
    kind, _ = _type(column)
    if kind != "varchar":
        raise SimulationError(f"{table.name}.{column.name}: no discriminator of {column.type}")
    statistics = column.statistics
    empty: list[object] = [None] * statistics.nulls
    for sentinel in statistics.sentinels:
        empty += [sentinel.value] * sentinel.rows
    if len(empty) != kinds.count(None):
        raise SimulationError(
            f"{table.name}.{column.name}: its nulls and sentinels are not the rows of no entity"
        )
    random.shuffle(empty)
    rest = iter(empty)
    return [next(rest) if found is None else found[1] for found in kinds]


def _within(
    table: Table,
    column: Column,
    discriminator: Discriminator,
    order: list[int],
    kinds: list[tuple[int, str] | None],
) -> list[int]:
    """`order`, the rows of each entity that `column` is not filled in first, as many as it counts.

    Within each entity, and within the rows of none, the rows keep their order, so that the columns
    of a group are filled in the same rows of each.
    """
    statistics = column.statistics
    present = table.rows - statistics.nulls - statistics.sentinel_rows
    segments: dict[int | None, list[int]] = {}
    for row in order:
        found = kinds[row]
        segments.setdefault(None if found is None else found[0], []).append(row)
    wanted: dict[int | None, int] = {
        index: entity.filled[column.name] for index, entity in enumerate(discriminator.entities)
    }
    wanted[None] = present - sum(wanted.values())
    empty: list[int] = []
    filled: list[int] = []
    for index, count in wanted.items():
        rows = segments.get(index, [])
        if not 0 <= count <= len(rows):
            of = "an entity" if index is not None else "no entity"
            raise SimulationError(
                f"{table.name}.{column.name}: filled in {count} rows of {of}, of {len(rows)}"
            )
        empty += rows[: len(rows) - count]
        filled += rows[len(rows) - count :]
    return empty + filled


def _values(
    table: Table,
    column: Column,
    order: list[int],
    random: Random,
    pool: _Pool,
    most: int | None,
) -> list[object]:
    """The values of `column`, one per row of `table`, its nulls and sentinels first in `order`.

    The values are those of `pool`. Where `most` is given, each of those that fill rows is in as
    many rows at most, and the first of them in as many.
    """
    statistics = column.statistics
    sentinels = statistics.sentinel_rows
    present = table.rows - statistics.nulls - sentinels
    if present < 0 or statistics.distinct > present or (present > 0 and statistics.distinct == 0):
        raise SimulationError(
            f"{table.name}.{column.name}: {statistics.distinct} distinct values, "
            f"{statistics.nulls} nulls and {sentinels} sentinels do not fit {table.rows} rows"
        )
    held, filled = pool.filling, present - len(pool.once)
    values = pool.once + (
        [*held, *random.choices(held, k=filled - len(held))]
        if most is None
        else _spread(table, column, held, filled, most, random)
    )
    # The condition of a column is met by the values as they repeat, not by the pool alone.
    if column.matches:
        kind = column.matches[0].type
        texts = [str(value) for value in values]
        if kind.detector.share(texts) < kind.detector.threshold:
            raise SimulationError(
                f"{table.name}.{column.name}: {statistics.distinct} distinct values of"
                f" {present} are no {kind.name} together"
            )
    empty: list[object] = [None] * statistics.nulls
    for sentinel in statistics.sentinels:
        empty += [_sentinel(table, column, sentinel.value)] * sentinel.rows
    random.shuffle(empty)
    random.shuffle(values)
    placed: list[object] = [None] * table.rows
    for row, value in zip(order, [*empty, *values], strict=True):
        placed[row] = value
    return placed


def _spread(
    table: Table, column: Column, pool: list[object], present: int, most: int, random: Random
) -> list[object]:
    """`present` values of `pool`, each once at least and `most` times at most, the first `most`."""
    if not pool or len(pool) * most < present or len(pool) + most - 1 > present:
        raise SimulationError(
            f"{table.name}.{column.name}: {len(pool)} values of {most} rows at most do not fill"
            f" {present} rows"
        )
    counts = {value: 1 for value in pool}
    counts[pool[0]] = most
    growing = pool[1:]
    for _ in range(present - len(pool) - most + 1):
        place = random.randrange(len(growing))
        counts[growing[place]] += 1
        if counts[growing[place]] == most:
            growing[place] = growing[-1]
            growing.pop()
    return [value for value, rows in counts.items() for _ in range(rows)]


def _sentinel(table: Table, column: Column, text: str) -> object:
    """The sentinel `text` of `column`, of its type: a text as it is, or a day or a moment."""
    kind, _ = _type(column)
    try:
        if kind == "varchar":
            return text
        if kind == "date":
            return date.fromisoformat(text)
        if kind == "timestamp":
            return datetime.fromisoformat(text)
    except ValueError as error:
        raise SimulationError(
            f"{table.name}.{column.name}: a sentinel is no day in the form of ISO 8601"
        ) from error
    raise SimulationError(f"{table.name}.{column.name}: no sentinel of {column.type} is made")


def _pool(table: Table, column: Column, random: Random) -> list[object]:
    """As many distinct values of the type of `column` as its statistics count."""
    count = column.statistics.distinct
    kind, parameters = _type(column)
    if count == 0:
        return []
    try:
        if kind in _INTEGERS:
            return list(_integers(table, column, kind, random))
        if kind == "decimal" and parameters:
            precision, scale = (*parameters, 0)[:2]
            numbers = random.sample(range(10**precision), count)
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
    return _drawn(table, column, kind, random)


def _drawn(table: Table, column: Column, kind: str, random: Random) -> list[object]:
    """The distinct values of `column` of the type `kind`, of those drawn one by one.

    Raises:
        SimulationError: The type is not generated, or its values cannot be drawn.
    """
    if kind == "double":
        return _distinct(
            f"{table.name}.{column.name}",
            column.statistics.distinct,
            lambda: round(random.uniform(0, 10**6), 4),
        )
    if kind == "uuid":
        return _distinct(
            f"{table.name}.{column.name}", column.statistics.distinct, lambda: _uuid(0, random)
        )
    if kind == "varchar":
        return _texts(table, column, random)
    raise SimulationError(f"{table.name}.{column.name}: the type {column.type} is not generated")


def _integers(table: Table, column: Column, kind: str, random: Random) -> list[int]:
    """The distinct whole numbers of `column`, within its range where it has one, of both its ends.

    Of a range, they are in their order, as positions are numbered, and all of it where they are
    as many, as a key numbered from one.

    Raises:
        SimulationError: The range is of no whole numbers, or of other values than the column
            counts: fewer, or one other than its ends.
    """
    count = column.statistics.distinct
    found = column.statistics.range
    if found is None or found.smallest is None or found.largest is None:
        return list(random.sample(range(1, _INTEGERS[kind]), count))
    try:
        smallest, largest = int(found.smallest), int(found.largest)
    except ValueError as error:
        raise SimulationError(f"{table.name}.{column.name}: a range of no whole numbers") from error
    if largest - smallest + 1 < count or (count == 1) != (smallest == largest):
        raise SimulationError(
            f"{table.name}.{column.name}: {count} distinct values do not fit their range"
        )
    if count == 1:
        return [smallest]
    return sorted([smallest, *random.sample(range(smallest + 1, largest), count - 2), largest])


def _type(column: Column) -> tuple[str, tuple[int, ...]]:
    """The type of `column`, without its parameters, and its parameters of numbers, if any."""
    match = re.fullmatch(r"(\w+)(?:\((\d+)(?:,\s*(\d+))?\))?", column.type)
    if match is None:
        return column.type, ()
    return match.group(1), tuple(int(number) for number in match.groups()[1:] if number)


def _texts(table: Table, column: Column, random: Random) -> list[object]:
    """The distinct texts of `column`, of its lengths: its shortest and its longest among them.

    They are lists of the values of its items where the column is one of lists, else of the first
    semantic type of the column where it has a match, else letters.
    """
    where = f"{table.name}.{column.name}"
    lengths = column.statistics.lengths
    if lengths is None:
        raise SimulationError(f"{where}: a text column without its lengths")
    if column.list_separator is None:
        draw = _drawing(where, column.matches, lengths, _letters, random)
        return _distinct(where, column.statistics.distinct, draw)
    items = column.items
    separator = column.list_separator
    if items is None or items.statistics.lengths is None:
        raise SimulationError(f"{where}: a column of lists without the lengths of its items")
    item = _drawing(f"{where}, its items", items.matches, items.statistics.lengths, _digits, random)
    pool: dict[int, list[str]] = {}
    for value in _distinct(f"{where}, its items", items.statistics.distinct, item):
        pool.setdefault(len(str(value)), []).append(str(value))
    unused = {value for values in pool.values() for value in values}
    wanted = iter([lengths.shortest, lengths.longest])

    def listed() -> str:
        given = next(wanted, None)
        # Each try of a length of its own, as not every length is one of values of the pool.
        for _ in range(_ATTEMPTS):
            text = _list(_length(given, lengths, random), separator, pool, unused, random)
            if text is not None:
                return text
        within = given if given is not None else f"{lengths.shortest} to {lengths.longest}"
        raise SimulationError(f"{where}: no list of {within} characters can be made")

    texts = _distinct(where, column.statistics.distinct, listed)
    if unused:
        raise SimulationError(
            f"{where}: {len(texts)} lists cannot hold the {items.statistics.distinct} values of"
            " its items"
        )
    if not is_list(texts, separator, ()):
        raise SimulationError(f"{where}: lists of the values of its items are no lists of values")
    return texts


def _drawing(
    where: str,
    matches: tuple[Match, ...],
    lengths: Lengths,
    plain: Callable[[int, Random], str],
    random: Random,
) -> Callable[[], str]:
    """How a text of `lengths` is drawn: of the first type of `matches`, else by `plain`.

    The shortest and the longest are drawn first, the others of a length between them at random.
    """
    wanted = iter([lengths.shortest, lengths.longest])
    kind = matches[0].type if matches else None
    typed = None if kind is None else _TYPED.get(kind)
    if kind is not None and typed is None:
        raise SimulationError(f"{where}: no {kind.name} is made, a semantic type of a project")

    def draw() -> str:
        given = next(wanted, None)
        if kind is None or typed is None:
            return plain(_length(given, lengths, random), random)
        # Each try of a length of its own, as not every length between the shortest and the
        # longest is one of a value of the type.
        for _ in range(_ATTEMPTS):
            length = _length(given, lengths, random)
            text = typed(length, random)
            if len(text) == length and kind.detector.recognises(text):
                return text
        within = given if given is not None else f"{lengths.shortest} to {lengths.longest}"
        raise SimulationError(f"{where}: no {kind.name} of {within} characters can be made")

    return draw


def _length(given: int | None, lengths: Lengths, random: Random) -> int:
    """`given`, or where it is None a length from the shortest to the longest, at random."""
    return given if given is not None else random.randint(lengths.shortest, lengths.longest)


def _list(
    length: int, separator: str, pool: dict[int, list[str]], unused: set[str], random: Random
) -> str | None:
    """A list of values of `pool`, by their lengths, joined by `separator`, of `length` characters.

    Of the values of a length, those `unused` are drawn first, and taken from it, so that the lists
    hold every value of the pool. None where the values drawn leave a rest no value of it fills.
    """
    shortest = min(pool)
    sizes = []
    left = length
    while left not in pool or (left > 2 * shortest and random.random() < _LONGER):
        # A value short enough that another of the shortest still follows it.
        fitting = [size for size in pool if left - size - len(separator) >= shortest]
        if not fitting:
            return None
        sizes.append(random.choice(fitting))
        left -= sizes[-1] + len(separator)
    values = []
    for size in (*sizes, left):
        value = random.choice([value for value in pool[size] if value in unused] or pool[size])
        unused.discard(value)
        values.append(value)
    return separator.join(values)


def _email(length: int, random: Random) -> str:
    """An e-mail address that may be of `length` characters."""
    domain = max(1, (length - 4) // 3)
    return f"{_letters(length - domain - 4, random)}@{_letters(domain, random)}.de"


def _phone(length: int, random: Random) -> str:
    """A German phone number that may be of `length` characters."""
    prefix = random.choice(_PHONES)
    return prefix + _digits(length - len(prefix), random)


def _postal_code(length: int, random: Random) -> str:
    """A postal code that may be of `length` characters."""
    return _digits(length, random)


def _iban(length: int, random: Random) -> str:
    """A German IBAN, in groups of four where `length` is theirs."""
    # The bank of eight digits and the account of ten; in groups of four, it is five characters
    # longer.
    number = "DE00" + _digits(18, random)
    number = number[:2] + calc_check_digits(number) + number[4:]
    grouped = " ".join(number[start : start + 4] for start in range(0, len(number), 4))
    return grouped if length == len(grouped) else number


def _card_number(length: int, random: Random) -> str:
    """A card number of Visa or Mastercard of `length` digits, with its check digit."""
    number = random.choice("45") + _digits(length - 2, random)
    return number + calc_check_digit(number)


def _date(length: int, random: Random) -> str:
    """A date as text, of a form of `length` characters where there is one."""
    moment = _START + timedelta(seconds=random.randrange(_DAYS * 86400))
    return moment.strftime(random.choice(_DATES.get(length, ("",))))


def _uuid(_: int, random: Random) -> str:
    """A UUID of version 4, whose length is always the same."""
    return str(uuid.UUID(int=random.getrandbits(128), version=4))


def _free_text(length: int, random: Random) -> str:
    """A comment in German of `length` characters, its last word cut where it is too long."""
    words = [random.choice(_FIRST)]
    while sum(map(len, words)) + len(words) - 1 < length:
        words.append(random.choice(_WORDS))
    return " ".join(words)[:length]


def _one_of(*spellings: str) -> Callable[[int, Random], str]:
    """How a text is made of fixed spellings: one of `spellings` of the length asked for, at random.

    A word of a type written in several cases is given in each of them, its `cases`.
    """

    def made(length: int, random: Random) -> str:
        return random.choice([text for text in spellings if len(text) == length] or [""])

    return made


# How a text is made that may be of a semantic type of the tool and of a length, which the caller
# is to tell: making test data is no concern of the tool.
_TYPED: Final[dict[SemanticType, Callable[[int, Random], str]]] = {
    EMAIL: _email,
    PHONE: _phone,
    POSTAL_CODE: _postal_code,
    IBAN: _iban,
    CARD_NUMBER: _card_number,
    DATE: _date,
    UUID: _uuid,
    FREE_TEXT: _free_text,
    TRUE_FALSE: _one_of(*cases("true", "false")),
    YES_NO: _one_of(*cases("yes", "no")),
    ZERO_ONE: _one_of("0", "1"),
    CURRENCY_CODE: _one_of(*CODES),
    CURRENCY_NUMBER: _one_of(*NUMBERS),
    CURRENCY_NAME: _one_of(*cases(*NAMES)),
}


def _letters(length: int, random: Random) -> str:
    """A text of `length` lower case letters."""
    return "".join(random.choices(ascii_lowercase, k=length))


def _digits(length: int, random: Random) -> str:
    """A text of `length` digits."""
    return "".join(random.choices(digits, k=length))


def _distinct(where: str, count: int, draw: Callable[[], object]) -> list[object]:
    """`count` distinct values drawn by `draw`, of the column `where`."""
    pool: dict[object, None] = {}
    for _ in range(_ATTEMPTS * count):
        pool[draw()] = None
        if len(pool) == count:
            return list(pool)
    raise SimulationError(f"{where}: {count} distinct values cannot be drawn")
