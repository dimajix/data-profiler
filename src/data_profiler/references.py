"""The references of the tables of a profile: their columns whose values are those of a key.

A reference is of one column, to a key of one column of a table, of another or of the same. As a
schema may have thousands of columns and hundreds of keys, the references are indicated before any
of them is verified, by the profile alone, without a query: a column whose type identifies a row may
refer to a key whose type is of the family of its own, whose distinct values are as many as its own
at least, as far as those outside of the key, in rows whose reference is lost, leave, whose lengths
hold its own, whose matches share one with its own, where both have any, and whose range overlaps
its own. A column of lists is indicated by the values of its lists, `Column.as_items`, whose
statistics and matches are those of a column of them; they are texts, compared with a key of whole
numbers as its numbers where they are digits, their range, counted as texts, not known where they
are of several lengths, as `999` comes after `1000`. A column of lists is not searched for a
reference to a key of its own table, nor measured where it is given one, as its values are read on a
source that reads its table as a row of each of them, and would read the key so as well.
Unmistakable values, of a type such as `uuid` or of a column whose match is a UUID, refer to
unmistakable values alone. Whole numbers that are a run from the start of the key - nearly every
value from the smallest of the key up to their largest -, short of its end, as a code or a counter
is, or a key of their own table, as a key numbered from one is within any other numbered from one of
as many values or more, refer to it only where their name agrees with it: it holds the terms of the
name of the key and of its table. A range is compared as numbers where the column is of no text, or
of the values of lists compared as numbers, else as texts.

Each reference indicated is probed: `_PROBES` values of its column, taken at random, looked up in
the whole key by the database, so that no value leaves it, the keys of a query `PER_QUERY` of the
module `source` at most and its columns `PROBES_PER_QUERY`, each column taken by a sampled read of
its own, which ends once it has taken them. A pair of random samples of two tables would say
nothing, as they hold few of the same rows. A column of unmistakable values refers to a key where
more than `_UNMISTAKABLE` of its values are found, as one found tells where they come from; another
is dropped where fewer than `_PROBED` are found, and its coverage counted on the whole table, the
references of a query `PER_QUERY` at most: it refers to the key where `_COVERAGE` of its values,
nulls and sentinels aside, are found in it. A column of lists is probed and counted on a source of a
row of each value of its lists, `Source.unnested`, by queries of its own, so that the rows of no
other column are repeated; its reference is many to many.

A column of unmistakable values refers to the key of the most values found, then of the table of the
fewest rows, the most specific. Another that refers to one key alone has that reference; one that
refers to several has each as a reference candidate, none of them preferred, ranked by how the span
of its values fits the one expected of as many values chosen at random of the key, then by whether
its name agrees with the key, then by the rows of the table of the key. A column the overrides give
a reference of is not searched, but measured - its coverage counted, or its values probed where they
are unmistakable - and warned of where that falls below what a reference is found at, or where the
column referred to is no key of one column; a column given none has no reference and no reference
candidates, and is not probed. The references name columns and tables alone, and no values of the
database.
"""

import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from itertools import batched, groupby
from typing import Final

from data_profiler.detect import UUID
from data_profiler.glossary import terms
from data_profiler.overrides import GivenReferences
from data_profiler.profile import DIGITS, Column, Profile, Range, Reference, Table
from data_profiler.source import PER_QUERY, PROBES_PER_QUERY, Dialect, Lookup, Probe, Source
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

    @property
    def filled(self) -> int:
        """How many rows of its table the column is filled in; of lists, its rows, not its values.

        A list holds one value at least, so that the rows of the lists of a column of lists are as
        many as its values at least, which a share of them taken holds as many of.
        """
        return self.table.filled(self.column.name)

    @property
    def separator(self) -> str | None:
        """The separator of the lists of the column, where it refers by their values, else None."""
        return self.table.column(self.column.name).items_separator


def find(source: Source, profile: Profile, given: Mapping[str, GivenReferences]) -> Profile:
    """`profile`, each table with the references and reference candidates of its columns.

    Args:
        source: The schema of the profile.
        profile: The profile, its tables with their keys, and their columns with their statistics
            and matches.
        given: The references the overrides give, the key or False, by the names of the tables
            and of the columns they are given of, which the profile has, as their keys do.

    Returns:
        The profile, each table with the references and the reference candidates of its columns,
        found or given, those it had replaced: each given as given, measured, and none of a column
        given none; none where none is found, with no query where none is indicated and none given.

    Raises:
        SourceError: The database fails to list the columns of a table of a column of lists, to
            probe the references or to count their coverage.
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
        _Pair(table, column.as_items, target, key)
        for table in profile.tables
        for column in table.columns
        if column.name not in given.get(table.name, {})
        and table.filled(column.name) > 0
        and dialect.identifies(column.type)
        for target, key in keys
        if (target.name, key.name) != (table.name, column.name)
        and not _of_its_lists(table, column, target)
        and _indicated(dialect, _Pair(table, column.as_items, target, key))
    ]
    found: list[tuple[_Pair, float]] = []
    counting = []
    for pair, share in zip(pairs, _on_sources(source, pairs, _probed), strict=True):
        if _unmistakable(dialect, pair.column):
            if share > _UNMISTAKABLE:
                found.append((pair, share))
        elif share >= _PROBED:
            counting.append(pair)
    covered = [
        (pair, coverage)
        for pair, coverage in zip(counting, _on_sources(source, counting, _covered), strict=True)
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
        "Found the references of %d tables: %d, and %d reference candidates",
        len(tables),
        sum(len(table.references) for table in tables),
        sum(len(table.reference_candidates) for table in tables),
    )
    return replace(profile, tables=tables)


def _measured(
    source: Source, profile: Profile, given: Mapping[str, GivenReferences]
) -> list[tuple[Reference, str]]:
    """The references `given`, with the tables that refer, measured as those found are.

    The coverage of each is counted, or unmistakable values probed, and warned of where it falls
    below what a reference is found at, or the column referred to is no key of one column; it is
    the reference all the same, as the overrides are of all environments. A column of lists given a
    key of its own table is not measured, but warned of, as its values would be read with the key.
    """
    dialect = source.dialect
    pairs = [
        _Pair(table, table.column(name).as_items, target, target.column(key.column))
        for table in profile.tables
        for name, key in given.get(table.name, {}).items()
        if key is not False
        for target in (profile.table(key.table),)
    ]
    unmeasured = [
        pair
        for pair in pairs
        if _of_its_lists(pair.table, pair.table.column(pair.column.name), pair.target)
    ]
    for pair in unmeasured:
        _warn(pair, "a key of the table of its lists, which is not measured")
    measured = [pair for pair in pairs if pair not in unmeasured]
    probing = [pair for pair in measured if _unmistakable(dialect, pair.column)]
    counting = [pair for pair in measured if not _unmistakable(dialect, pair.column)]
    for pair, share in zip(probing, _on_sources(source, probing, _probed), strict=True):
        if share <= _UNMISTAKABLE:
            _warn(pair, "most of whose values probed are not found in it")
    coverages = dict(zip(counting, _on_sources(source, counting, _covered), strict=True))
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


def _unmistakable(dialect: Dialect, column: Column) -> bool:
    """Whether the values of `column` are equal to those of another by no chance: UUIDs."""
    return dialect.is_unmistakable(column.type) or any(
        match.type == UUID for match in column.matches
    )


def _numeric(dialect: Dialect, column: Column) -> bool:
    """Whether the range of `column` is one of numbers where its ends read as numbers."""
    return not dialect.is_text(column.type) and not _unmistakable(dialect, column)


def _of_its_lists(table: Table, column: Column, target: Table) -> bool:
    """Whether `column` of `table` is one of lists that would refer to a key of its own table.

    Its values are read on a source that reads its table as a row of each of them, which would read
    the key so as well; such a reference is not searched, nor measured where it is given.
    """
    return column.items_separator is not None and target.name == table.name


def _as_numbers(dialect: Dialect, pair: _Pair) -> bool:
    """Whether the values of the column of `pair` are compared with its key as numbers.

    The values of lists are texts, of digits where they refer to a key of whole numbers, whose
    values they are as text: they are compared as the numbers of the key are.
    """
    key = pair.key.type
    if (
        pair.separator is not None
        and dialect.is_surrogate(key)
        and not dialect.is_unmistakable(key)
    ):
        return _whole(pair.column.statistics.range, numeric=True) is not None
    return _numeric(dialect, pair.column)


def _range(dialect: Dialect, pair: _Pair) -> Range | None:
    """The range of the column of `pair` as it is compared with its key, or None where not known.

    The range of values of lists is counted as text, whose order is not that of the numbers of
    digits of several lengths, `999` after `1000`: compared as numbers, it is not known.
    """
    lengths = pair.column.statistics.lengths
    several = lengths is None or lengths.shortest != lengths.longest
    if pair.separator is not None and several and _as_numbers(dialect, pair):
        return None
    return pair.column.statistics.range


def _indicated(dialect: Dialect, pair: _Pair) -> bool:
    """Whether the profile indicates that the column of `pair` refers to its key."""
    column, key = pair.column.statistics, pair.key.statistics
    unmistakable = _unmistakable(dialect, pair.column)
    if unmistakable != _unmistakable(dialect, pair.key):
        return False
    # Unmistakable values are compared as text whatever their types: UUIDs of the type and as text;
    # values of lists as the numbers of their key where they are numbers.
    numeric = _as_numbers(dialect, pair)
    listed = pair.separator is not None and numeric
    if (
        not unmistakable
        and not listed
        and not dialect.is_same_family(pair.column.type, pair.key.type)
    ):
        return False
    # Those outside of the key are in one row each at most.
    outside = (1 - _COVERAGE) * pair.filled
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
    overlapping = _overlaps(_range(dialect, pair), key.range, numeric=numeric)
    return overlapping and (not _run(dialect, pair, numeric=numeric) or _named(pair))


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


def _run(dialect: Dialect, pair: _Pair, *, numeric: bool) -> bool:
    """Whether the column of `pair` is a run its key holds by chance, unless its name agrees.

    A run is of whole numbers from the start of the key, nearly all of the values from its smallest
    up to their largest: short of its end, as a code or a counter is, or a key of the table of the
    column, as a key numbered from one is within any other numbered from one of as many values or
    more. Another column that holds nearly every value of the key refers to it whatever its name.
    """
    column = _whole(_range(dialect, pair), numeric=numeric)
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
    numeric = _as_numbers(dialect, pair)
    column = _whole(_range(dialect, pair), numeric=numeric)
    key = _whole(pair.key.statistics.range, numeric=numeric)
    if column is None or key is None or key[1] == key[0]:
        return 0.0
    distinct = pair.column.statistics.distinct
    expected = (distinct - 1) / (distinct + 1)
    return abs((column[1] - column[0]) / (key[1] - key[0]) - expected)


def _rank(dialect: Dialect, pair: _Pair) -> tuple[float, bool, int]:
    """How `pair` is ranked among the reference candidates of its column: the best fitting first."""
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
        # Stable, so that the reference candidates of a column keep their ranks.
        return tuple(sorted(found, key=lambda reference: places[reference.column]))

    return replace(
        table,
        references=ordered(references.get(table.name, [])),
        reference_candidates=ordered(candidates.get(table.name, [])),
    )


def _on_sources(
    source: Source,
    pairs: Sequence[_Pair],
    measure: Callable[[Source, Sequence[_Pair]], list[float]],
) -> list[float]:
    """Of each of `pairs`, the share `measure` gives of it, of a column of lists by its values.

    The pairs of a column of lists are measured on a source of a row of each value of its lists,
    those of each such column on their own, so that the rows of no other column are repeated; the
    others on `source`, together.
    """
    shares = [0.0] * len(pairs)
    # Of each column of lists its table, its name and its separator; of the others none.
    groups: dict[tuple[str, str, str] | None, list[int]] = {}
    for place, pair in enumerate(pairs):
        separator = pair.separator
        group = None if separator is None else (*pair.referring, separator)
        groups.setdefault(group, []).append(place)
    for group, places in groups.items():
        on = source if group is None else source.unnested(*group)
        for place, share in zip(
            places, measure(on, [pairs[place] for place in places]), strict=True
        ):
            shares[place] = share
    return shares


def _probed(source: Source, pairs: Sequence[_Pair]) -> list[float]:
    """Of each of `pairs`, the share of the values probed of its column found in its key.

    A column of pairs of keys of several queries is probed by each, of values taken anew.
    """
    dialect = source.dialect
    keys = list(dict.fromkeys(pair.referred for pair in pairs))
    shares: dict[_Pair, float] = {}
    for batch in batched(keys, PER_QUERY, strict=False):
        within = [pair for pair in pairs if pair.referred in batch]
        # One probe of each column, of whichever of its pairs.
        probing = list({pair.referring: pair for pair in within}.values())
        found: dict[tuple[tuple[str, str], tuple[str, str]], float] = {}
        where = "the references"
        for part in batched(probing, PROBES_PER_QUERY, strict=False):
            columns = [pair.referring for pair in part]
            statement = dialect.probed([_probe(dialect, pair) for pair in part], batch, _PROBES)
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
    share = min(100.0, 100.0 * _SPARE * _PROBES / max(1, pair.filled))
    return Probe(pair.table.name, pair.values(dialect), share)


def _covered(source: Source, pairs: Sequence[_Pair]) -> list[float]:
    """Of each of `pairs`, the share of the values of its column found in its key, on the table."""
    dialect = source.dialect
    coverages = [0.0] * len(pairs)
    tables = list(dict.fromkeys(pair.table.name for pair in pairs))
    for name in tables:
        places = [place for place, pair in enumerate(pairs) if pair.table.name == name]
        for batch in batched(places, PER_QUERY, strict=False):
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
