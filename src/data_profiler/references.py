"""The references of the tables of a profile: their columns whose values are those of a key.

A reference is of one column, to a key of one column of a table, of another or of the same. As a
schema may have thousands of columns and hundreds of keys, the references are indicated before any
of them is verified, by the profile alone, without a query: a column whose type identifies a row may
refer to a key whose type is of the family of its own, whose distinct values are as many as its own
at least, as far as those outside of the key, in rows whose reference is lost, leave, whose lengths
hold its own, whose matches share one with its own, where both have any, and whose range overlaps
its own. Unmistakable values, of a type such as `uuid` or of a column whose match is a UUID, refer
to unmistakable values alone. Whole numbers that are a run from the start of the key - nearly every
value from the smallest of the key up to their largest -, short of its end, as a code or a counter
is, or a key of their own table, as a key numbered from one is within any other numbered from one of
as many values or more, refer to it only where their name agrees with it: it holds the terms of the
name of the key and of its table. A range is compared as numbers where the column is of no text,
else as texts.

Each reference indicated is probed: `_PROBES` values of its column, taken at random, looked up in
the whole key by the database, so that no value leaves it, the keys of a query `_PER_QUERY` at most,
each column taken by a sampled read of its own, which ends once it has taken them. A pair of random
samples of two tables would say nothing, as they hold few of the same rows. A column of unmistakable
values refers to a key where more than `_UNMISTAKABLE` of its values are found, as one found tells
where they come from; another is dropped where fewer than `_PROBED` are found, and its coverage
counted on the whole table, the references of a query `_PER_QUERY` at most: it refers to the key
where `_COVERAGE` of its values, nulls and sentinels aside, are found in it.

A column of unmistakable values refers to the key of the most values found, then of the table of the
fewest rows, the most specific. Another that refers to one key alone has that reference; one that
refers to several has each as a candidate, none of them preferred, ranked by how the span of its
values fits the one expected of as many values chosen at random of the key, then by whether its name
agrees with the key, then by the rows of the table of the key. A column the overrides give a
reference of is not searched, but measured - its coverage counted, or its values probed where they
are unmistakable - and warned of where that falls below what a reference is found at, or where the
column referred to is no key of one column; a column given none has no reference and no candidates,
and is not probed. The references name columns and tables alone, and no values of the database.
"""

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from itertools import groupby
from typing import Final

from data_profiler.detect import UUID
from data_profiler.glossary import terms
from data_profiler.overrides import GivenReferences
from data_profiler.profile import DIGITS, Column, Profile, Range, Reference, Table
from data_profiler.source import Dialect, Lookup, Probe, Source
from data_profiler.values import counted

_logger = logging.getLogger(__name__)

# How many times the standard error the dialect counts distinct values with the approximate
# distinct count of a column may lie above that of its key.
_ERRORS: Final = 4
# The values taken of a column to probe it, and how many times as many rows the share of its table
# taken is to hold, so that it holds as many values.
_PROBES: Final = 100
_SPARE: Final = 4
# The share of the values probed found in the key above which unmistakable values refer to it, and
# below which others are dropped: three standard errors of a sample of 100 below `_COVERAGE`.
_UNMISTAKABLE: Final = 0.5
_PROBED: Final = 0.8
# The share of the values found in the key at which a column refers to it.
_COVERAGE: Final = 0.9
# The share of the values from the smallest of the key up to its own largest a run of whole numbers
# holds at least, and the share of the span of the key a short run spans at most.
_RUN: Final = 0.9
# The keys probed in one query, and the references counted in one, at most.
_PER_QUERY: Final = 10


# Not compared by its fields, but told apart as itself, so that tables and columns are not hashed
# where it is a key of a dict.
@dataclass(frozen=True, eq=False)
class _Pair:
    """A column of a table and a key of one column of a table it may refer to.

    Attributes:
        table: The table of the column.
        column: The column that may refer.
        target: The table of the key.
        key: The column of the key.
    """

    table: Table
    column: Column
    target: Table
    key: Column

    @property
    def referring(self) -> tuple[str, str]:
        """The names of the table and the column that may refer, which its references are of."""
        return self.table.name, self.column.name

    @property
    def referred(self) -> tuple[str, str]:
        """The names of the table and the column of the key."""
        return self.target.name, self.key.name

    def reference(self, coverage: float | None) -> Reference:
        """The reference of the column to the key, of `coverage`."""
        return Reference(self.column.name, self.target.name, self.key.name, coverage)

    def values(self, dialect: Dialect) -> str:
        """The expression of the values of the column, its sentinels left aside as nulls."""
        return dialect.without(self.column.name, self.column.type, self.column.left_aside)


def find(source: Source, profile: Profile, given: Mapping[str, GivenReferences]) -> Profile:
    """`profile`, each table with the references and candidates of its columns, found or given.

    Args:
        source: The schema of the profile.
        profile: The profile, its tables with their keys, and their columns with their statistics
            and matches.
        given: The references the overrides give, the key or False, by the names of the tables
            and of the columns they are given of, which the profile has, as their keys do.

    Returns:
        The profile, each table with the references and the candidates of its columns, those it had
        replaced: each given as given, measured, and none of a column given none; none where none
        is found, with no query where none is indicated and none given.

    Raises:
        SourceError: The database fails to probe the references or to count their coverage.
    """
    dialect = source.dialect
    keys = [
        (table, table.column(name))
        for table in profile.tables
        if table.rows
        for (name, *more) in table.keys
        if not more
    ]
    pairs = [
        _Pair(table, column, target, key)
        for table in profile.tables
        for column in table.columns
        if column.name not in given.get(table.name, {})
        and _present(table, column) > 0
        and dialect.identifies(column.type)
        for target, key in keys
        if (target.name, key.name) != (table.name, column.name)
        and _indicated(dialect, _Pair(table, column, target, key))
    ]
    found: list[tuple[_Pair, float]] = []
    counting = []
    for pair, share in zip(pairs, _probed(source, pairs), strict=True):
        if _unmistakable(dialect, pair.column):
            if share > _UNMISTAKABLE:
                found.append((pair, share))
        elif share >= _PROBED:
            counting.append(pair)
    covered = [
        (pair, coverage)
        for pair, coverage in zip(counting, _covered(source, counting), strict=True)
        if coverage >= _COVERAGE
    ]
    references: dict[str, list[Reference]] = {}
    for reference, table in _measured(source, profile, given):
        references.setdefault(table, []).append(reference)
    candidates: dict[str, list[Reference]] = {}
    for pair, _ in _chosen(found):
        references.setdefault(pair.table.name, []).append(pair.reference(None))
    # The pairs are of the columns in their order, those of a column after each other.
    for (table, _), passing in groupby(covered, key=lambda found: found[0].referring):
        ranked = sorted(passing, key=lambda found: _rank(dialect, found[0]))
        named = [pair.reference(_rounded(coverage)) for pair, coverage in ranked]
        (references if len(named) == 1 else candidates).setdefault(table, []).extend(named)
    tables = tuple(_related(table, references, candidates) for table in profile.tables)
    _logger.info(
        "Found the references of %d tables: %d, and %d candidates",
        len(tables),
        sum(len(table.references) for table in tables),
        sum(len(table.candidates) for table in tables),
    )
    return replace(profile, tables=tables)


def _measured(
    source: Source, profile: Profile, given: Mapping[str, GivenReferences]
) -> list[tuple[Reference, str]]:
    """The references `given`, with the tables that refer, measured as those found are.

    The coverage of each is counted, or unmistakable values probed, and warned of where it falls
    below what a reference is found at, or the column referred to is no key of one column; it is
    the reference all the same, as the overrides are of all environments.
    """
    dialect = source.dialect
    pairs = [
        _Pair(table, table.column(name), target, target.column(key.column))
        for table in profile.tables
        for name, key in given.get(table.name, {}).items()
        if key is not False
        for target in (profile.table(key.table),)
    ]
    probing = [pair for pair in pairs if _unmistakable(dialect, pair.column)]
    counting = [pair for pair in pairs if not _unmistakable(dialect, pair.column)]
    for pair, share in zip(probing, _probed(source, probing), strict=True):
        if share <= _UNMISTAKABLE:
            _warn(pair, "most of whose values probed are not found in it")
    coverages = dict(zip(counting, _covered(source, counting), strict=True))
    for pair, coverage in coverages.items():
        if coverage < _COVERAGE:
            _warn(pair, f"which holds {coverage:.0%} of its values")
    for pair in pairs:
        if (pair.key.name,) not in pair.target.keys:
            _warn(pair, "which is no key of one column")
    return [
        (replace(pair.reference(_rounded(coverages.get(pair))), given=True), pair.table.name)
        for pair in pairs
    ]


def _rounded(coverage: float | None) -> float | None:
    """`coverage`, written with as many digits as a share found."""
    return None if coverage is None else round(coverage, DIGITS)


def _warn(pair: _Pair, what: str) -> None:
    """Warns that the overrides give the reference of `pair`, `what` is wrong of it."""
    _logger.warning(
        "The overrides give %s.%s as a reference to %s.%s, %s",
        pair.table.name,
        pair.column.name,
        pair.target.name,
        pair.key.name,
        what,
    )


def _present(table: Table, column: Column) -> int:
    """How many values `column` of `table` has, neither nulls nor sentinels."""
    statistics = column.statistics
    return table.rows - statistics.nulls - statistics.sentinel_rows


def _unmistakable(dialect: Dialect, column: Column) -> bool:
    """Whether the values of `column` are equal to those of another by no chance: UUIDs."""
    return dialect.is_unmistakable(column.type) or any(
        match.type == UUID for match in column.matches
    )


def _numeric(dialect: Dialect, column: Column) -> bool:
    """Whether the range of `column` is one of numbers where its ends read as numbers."""
    return not dialect.is_text(column.type) and not _unmistakable(dialect, column)


def _indicated(dialect: Dialect, pair: _Pair) -> bool:
    """Whether the profile indicates that the column of `pair` refers to its key."""
    column, key = pair.column.statistics, pair.key.statistics
    unmistakable = _unmistakable(dialect, pair.column)
    if unmistakable != _unmistakable(dialect, pair.key):
        return False
    # Unmistakable values are compared as text whatever their types: UUIDs of the type and as text.
    if not unmistakable and not dialect.is_same_family(pair.column.type, pair.key.type):
        return False
    # Those outside of the key are in one row each at most.
    outside = (1 - _COVERAGE) * _present(pair.table, pair.column)
    spread = 1 + _ERRORS * dialect.distinct_error()
    if column.distinct > spread * key.distinct + outside:
        return False
    # Lengths and matches are of the form of the values, which those outside share.
    if column.lengths is not None and key.lengths is not None:
        shortest, longest = column.lengths.shortest, column.lengths.longest
        if shortest < key.lengths.shortest or longest > key.lengths.longest:
            return False
    matched = {match.type for match in pair.column.matches}
    if matched and pair.key.matches and not matched & {match.type for match in pair.key.matches}:
        return False
    numeric = _numeric(dialect, pair.column)
    overlapping = _overlaps(column.range, key.range, numeric=numeric)
    return overlapping and (not _run(pair, numeric=numeric) or _named(pair))


def _overlaps(found: Range | None, key: Range | None, *, numeric: bool) -> bool:
    """Whether the range `found` overlaps the range `key`; true where either is not known.

    Not that it lies within it: the values outside of the key may lie beyond it. The ends are
    compared as numbers where they are `numeric` and read as numbers, else as texts.
    """
    column, keyed = _ends(found), _ends(key)
    if column is None or keyed is None:
        return True
    numbers, numbered = _numbers(column), _numbers(keyed)
    if numeric and numbers is not None and numbered is not None:
        return numbered[0] <= numbers[1] and numbers[0] <= numbered[1]
    return keyed[0] <= column[1] and column[0] <= keyed[1]


def _ends(found: Range | None) -> tuple[str, str] | None:
    """The smallest and the largest of `found`, where it has both."""
    if found is None or found.smallest is None or found.largest is None:
        return None
    return found.smallest, found.largest


def _numbers(ends: tuple[str, str]) -> tuple[Decimal, Decimal] | None:
    """The ends of a range as numbers, where both are finite ones."""
    try:
        numbers = Decimal(ends[0]), Decimal(ends[1])
    except InvalidOperation:
        return None
    return numbers if all(number.is_finite() for number in numbers) else None


def _whole(found: Range | None, *, numeric: bool) -> tuple[int, int] | None:
    """The smallest and the largest of `found`, where it is `numeric` and both are whole numbers."""
    ends = _ends(found)
    numbers = None if ends is None or not numeric else _numbers(ends)
    if numbers is None or any(number != number.to_integral_value() for number in numbers):
        return None
    return int(numbers[0]), int(numbers[1])


def _run(pair: _Pair, *, numeric: bool) -> bool:
    """Whether the column of `pair` is a run its key holds by chance, unless its name agrees.

    A run is of whole numbers from the start of the key, nearly all of the values from its smallest
    up to their largest: short of its end, as a code or a counter is, or a key of the table of the
    column, as a key numbered from one is within any other numbered from one of as many values or
    more. Another column that holds nearly every value of the key refers to it whatever its name.
    """
    column = _whole(pair.column.statistics.range, numeric=numeric)
    key = _whole(pair.key.statistics.range, numeric=numeric)
    if column is None or key is None:
        return False
    (_, largest), (lowest, highest) = column, key
    if pair.column.statistics.distinct < _RUN * (largest - lowest + 1):
        return False
    return largest - lowest <= _RUN * (highest - lowest) or (pair.column.name,) in pair.table.keys


def _named(pair: _Pair) -> bool:
    """Whether the name of the column of `pair` agrees with its key.

    It holds the terms of the name of the key and of the name of its table, as `cust_id` and
    `prnt_cust_id` do of the key `cust_id` of `cust`, or of the key `id` of it: a column whose name
    shares the prefix of its table alone, or the name of a key of another table, does not.
    """
    return set(terms(pair.target.name)) | set(terms(pair.key.name)) <= set(terms(pair.column.name))


def _misfit(dialect: Dialect, pair: _Pair) -> float:
    """How far the span of the values of the column of `pair` lies from the one expected.

    Of as many values chosen at random of the key, the span expected is the share
    `(d - 1) / (d + 1)` of the span of the key; of other than whole numbers, none is known.
    """
    numeric = _numeric(dialect, pair.column)
    column = _whole(pair.column.statistics.range, numeric=numeric)
    key = _whole(pair.key.statistics.range, numeric=numeric)
    if column is None or key is None or key[1] == key[0]:
        return 0.0
    distinct = pair.column.statistics.distinct
    expected = (distinct - 1) / (distinct + 1)
    return abs((column[1] - column[0]) / (key[1] - key[0]) - expected)


def _rank(dialect: Dialect, pair: _Pair) -> tuple[float, bool, int]:
    """How `pair` is ranked among the candidates of its column: the best fitting first."""
    return _misfit(dialect, pair), not _named(pair), pair.target.rows


def _chosen(found: Iterable[tuple[_Pair, float]]) -> list[tuple[_Pair, float]]:
    """Of the pairs `found` of each column, the one of the most found, then of the fewest rows."""
    chosen: dict[tuple[str, str], tuple[_Pair, float]] = {}
    for pair, share in found:
        kept = chosen.get(pair.referring)
        if kept is None or (share, -pair.target.rows) > (kept[1], -kept[0].target.rows):
            chosen[pair.referring] = pair, share
    return list(chosen.values())


def _related(
    table: Table, references: dict[str, list[Reference]], candidates: dict[str, list[Reference]]
) -> Table:
    """`table`, with its `references` and `candidates`, in the order of its columns."""
    places = {column.name: place for place, column in enumerate(table.columns)}

    def ordered(found: Sequence[Reference]) -> tuple[Reference, ...]:
        # Stable, so that the candidates of a column keep their ranks.
        return tuple(sorted(found, key=lambda reference: places[reference.column]))

    return replace(
        table,
        references=ordered(references.get(table.name, [])),
        candidates=ordered(candidates.get(table.name, [])),
    )


def _probed(source: Source, pairs: Sequence[_Pair]) -> list[float]:
    """Of each of `pairs`, the share of the values probed of its column found in its key.

    A column of pairs of keys of several queries is probed by each, of values taken anew.
    """
    dialect = source.dialect
    keys = list(dict.fromkeys(pair.referred for pair in pairs))
    shares: dict[_Pair, float] = {}
    for start in range(0, len(keys), _PER_QUERY):
        batch = keys[start : start + _PER_QUERY]
        within = [pair for pair in pairs if pair.referred in batch]
        # One probe of each column, of whichever of its pairs.
        probing = list({pair.referring: pair for pair in within}.values())
        columns = [pair.referring for pair in probing]
        statement = dialect.probed([_probe(dialect, pair) for pair in probing], batch, _PROBES)
        found: dict[tuple[tuple[str, str], tuple[str, str]], float] = {}
        where = "the references"
        for probe, key, taken, matched in source.query(statement, "probing the references"):
            share = counted(matched, where) / counted(taken, where)
            found[_place(probe, columns), _place(key, batch)] = share
        shares.update({pair: found.get((pair.referring, pair.referred), 0.0) for pair in within})
    return [shares[pair] for pair in pairs]


def _place[Placed](value: object, places: Sequence[Placed]) -> Placed:
    """The one of `places` at `value`, a place a query wrote of them.

    Raises:
        TypeError: The value is no place of them, which the dialect that wrote the query would
            have to make sure of.
    """
    if not isinstance(value, int) or not 0 <= value < len(places):
        raise TypeError("the query wrote a place of none of the references")
    return places[value]


def _probe(dialect: Dialect, pair: _Pair) -> Probe:
    """The probe of the column of `pair`, of a share of the rows of its table to take its values."""
    # A column of no values, given, is read whole.
    share = min(100.0, 100.0 * _SPARE * _PROBES / max(1, _present(pair.table, pair.column)))
    return Probe(pair.table.name, pair.values(dialect), share)


def _covered(source: Source, pairs: Sequence[_Pair]) -> list[float]:
    """Of each of `pairs`, the share of the values of its column found in its key, on the table."""
    dialect = source.dialect
    coverages = [0.0] * len(pairs)
    tables = list(dict.fromkeys(pair.table.name for pair in pairs))
    for name in tables:
        places = [place for place, pair in enumerate(pairs) if pair.table.name == name]
        for start in range(0, len(places), _PER_QUERY):
            batch = places[start : start + _PER_QUERY]
            lookups = [
                Lookup(pairs[place].values(dialect), *pairs[place].referred) for place in batch
            ]
            step = f"counting the references of {source.name(name)}"
            (row,) = source.query(dialect.covered(name, lookups), step)
            counts = [counted(found, name) for found in row]
            for index, place in enumerate(batch):
                values, found = counts[2 * index], counts[2 * index + 1]
                coverages[place] = found / values if values else 0.0
    return coverages
