"""The column dependencies of a table: its columns whose values follow from another, verified on it.

A column determines another where each of its values comes with one value of the other, in the rows
it is filled in, neither null nor a sentinel; a null of the other there is a value as any other. As
a table may have hundreds of columns, the dependencies are found in the sample before any is
verified. A determinant takes part where it is of a type whose values are exact, as the dialect
says, and filled in `_FEWEST` rows of the sample at least, a share `_REPEATED` of them at least of a
value that repeats: a value of one row says nothing, and a column of nearly none that repeat
determines every other by chance; a key of one column is none. A dependent takes part where it is of
a type whose values have an order, and departs from a constant in the rows of the values of the
determinant that repeat in more rows than it may depart from the determinant: any column determines
a constant, and a column of another entity, null in nearly all of them, or a flag of nearly one
value, follows from it by no dependency; a key of one column departs from every determinant. A
dependency holds in the sample where at most a share `_DEPARTING` of the rows of the determinant
depart from it - the rows of a value less those of the value of the dependent it comes with most
often -, as real data hold rows corrected and rows not; of a determinant, those of each dependent
are one dependency. Determinants that follow from each other, such as a code and its name, are
equivalent, and held together, the first in the table determining the others; the others are no
dependencies of their own. A column the overrides give as determining none takes no part as a
determinant, but as a dependent, so that a column equivalent to it determines on its own.

Of the dependencies found, the `_MOST` of the most columns that follow, then of the most rows of
values that repeat, are verified on the whole table, the others logged. Each is verified by queries
built from the building blocks of the dialect, which count the distinct values of the determinant
alone, and together with those of the others, exactly, `_PER_QUERY` at most in one: its strictness
is 1 - (together - alone) / alone, the share of the values of the determinant that come with one
value of the others, about. The determinant and all the others are counted together first; of a
dependency that falls short of `_STRICTNESS`, each of the others alone, and those that pass together
again, where they are several. Each equivalent determinant is counted the other way, with the first,
and is a dependent where that falls short. A dependency is held from `_STRICTNESS` on, with the
least strictness of its counts. The dependencies name columns alone, and no values of the database.
"""

import logging
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Final

from data_profiler.detect import is_filled
from data_profiler.profile import DIGITS, Column, ColumnDependency, Table
from data_profiler.source import Source
from data_profiler.values import counted
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)

# The rows of the sample a determinant is to be filled in at least, and the share of them of a
# value that repeats, at least; the share of them that may depart from a dependency in the sample.
_FEWEST: Final = 10
_REPEATED: Final = 0.5
_DEPARTING: Final = 0.01
# The strictness from which a dependency is held, the dependencies verified at most, and the
# distinct counts in one query at most.
_STRICTNESS: Final = 0.95
_MOST: Final = 50
_PER_QUERY: Final = 10


@dataclass(frozen=True)
class _Determinant:
    """A column that may determine others: the rows of the sample of each of its values that repeat.

    Attributes:
        column: The column.
        repeating: Of each of its values that repeat, its rows, the values of the most rows first.
        filled: The rows of the sample it is filled in.
    """

    column: Column
    repeating: tuple[tuple[int, ...], ...]
    filled: int

    @property
    def repeated(self) -> int:
        """The rows of the sample it holds a value in that repeats."""
        return sum(len(rows) for rows in self.repeating)

    def determines(self, values: Sequence[object]) -> bool:
        """Whether `values`, of a column of the sample, follow from it, as `_DEPARTING` allows.

        The rows that depart are, of each of its values, those less the rows of the value of
        `values` that comes with it most often; the values of the most rows are tried first, which
        give up the soonest. Values that a constant passes for as well, in the rows of its values
        that repeat, follow from it by no dependency, as any column determines a constant: those of
        a column of another entity, null in nearly all of them, or of a flag of nearly one value.
        """
        allowed = _DEPARTING * self.filled
        departing = 0
        for rows in self.repeating:
            departing += len(rows) - max(Counter(values[row] for row in rows).values())
            if departing > allowed:
                return False
        most = max(Counter(values[row] for rows in self.repeating for row in rows).values())
        return self.repeated - most > allowed


@dataclass(frozen=True)
class _Found:
    """A dependency found in the sample, before it is verified.

    Attributes:
        determinants: Its determinant, then those equivalent to it, in the order of the table.
        dependents: The columns that follow from it, in the order of the table.
        repeated: The rows of the sample its determinant holds a value in that repeats.
    """

    determinants: tuple[Column, ...]
    dependents: tuple[Column, ...]
    repeated: int

    @property
    def following(self) -> int:
        """How many columns follow from its determinant: its equivalents and its dependents."""
        return len(self.determinants) - 1 + len(self.dependents)


def determine(
    source: Source, table: Table, sample: Sample, determining_none: Collection[str]
) -> Table:
    """`table` with the dependencies of its columns, found in `sample` and verified on the table.

    Args:
        source: The schema the table is in.
        table: The table, its keys identified and its columns with their statistics, which name
            their sentinels.
        sample: The sample of the table, with the values of each of its columns.
        determining_none: The columns the overrides give as determining no other, which take no
            part as determinants, but as dependents.

    Returns:
        The table with its column dependencies, in the order of their determinants; none where none
        is found, with no query.

    Raises:
        SourceError: The database fails to count the values of the dependencies found.
    """
    found = _found(source, table, sample, determining_none)
    found.sort(key=lambda dependency: (-dependency.following, -dependency.repeated))
    if len(found) > _MOST:
        _logger.info(
            "Found %d column dependencies of %s in its sample, verifying %d, not those of %s",
            len(found),
            table.name,
            _MOST,
            ", ".join(dependency.determinants[0].name for dependency in found[_MOST:]),
        )
    verified = _verified(source, table, found[:_MOST])
    places = {column.name: place for place, column in enumerate(table.columns)}
    verified.sort(key=lambda dependency: places[dependency.determinants[0]])
    _logger.info("Determined the column dependencies of %s: %d", table.name, len(verified))
    return replace(table, column_dependencies=tuple(verified))


def _found(
    source: Source, table: Table, sample: Sample, determining_none: Collection[str]
) -> list[_Found]:
    """The dependencies of `table` that hold in `sample`, of no determinant determining none."""
    dialect = source.dialect
    # A key of one column, unique in the sample, takes part as neither: its values do not repeat,
    # and depart from every determinant whose values do.
    determinants = {
        column.name: determinant
        for column in table.columns
        if column.name not in determining_none and dialect.identifies(column.type)
        for determinant in [_determinant(column, sample)]
        if determinant is not None
    }
    following = [column for column in table.columns if dialect.is_ordered(column.type)]
    determined = {
        name: [
            column
            for column in following
            if column.name != name and determinant.determines(sample.columns[column.name])
        ]
        for name, determinant in determinants.items()
    }
    found = []
    absorbed: set[str] = set()
    for name, determinant in determinants.items():
        if name in absorbed:
            continue
        # Equivalent to it are those it determines that determine it.
        equivalent = [
            column
            for column in determined[name]
            if column.name in determinants
            and column.name not in absorbed
            and any(other.name == name for other in determined[column.name])
        ]
        absorbed.update(column.name for column in equivalent)
        equivalents = {column.name for column in equivalent}
        dependents = tuple(c for c in determined[name] if c.name not in equivalents)
        if equivalent or dependents:
            columns = (determinant.column, *equivalent)
            found.append(_Found(columns, dependents, determinant.repeated))
    return found


def _determinant(column: Column, sample: Sample) -> _Determinant | None:
    """`column` as a determinant of the others of `sample`; None where it takes no part.

    It takes part where it is filled in `_FEWEST` rows at least, a share `_REPEATED` of them of a
    value that repeats, and is not constant.
    """
    rows: dict[object, list[int]] = {}
    for index, value in enumerate(sample.columns[column.name]):
        if is_filled(value, column.left_aside):
            rows.setdefault(value, []).append(index)
    filled = sum(len(found) for found in rows.values())
    repeating = sorted((tuple(found) for found in rows.values() if len(found) > 1), key=len)
    determinant = _Determinant(column, tuple(reversed(repeating)), filled)
    if filled < _FEWEST or determinant.repeated < _REPEATED * filled or len(rows) < 2:
        return None
    return determinant


class _Counts:
    """The distinct counts of the values of a table, of its determinants alone and with others.

    The counts are asked for by `ask`, and counted by `count`, all those asked for since in as few
    queries as it can; each is counted once, and kept.
    """

    def __init__(self, source: Source, table: Table) -> None:
        self._source = source
        self._table = table
        self._asked: list[str] = []
        self._counted: dict[str, int] = {}

    def strictness(self, determinant: Column, others: Sequence[Column]) -> float:
        """How strictly `others` follow from `determinant`, as `count` counted them."""
        alone = self._counted[self._expression(determinant, ())]
        together = self._counted[self._expression(determinant, others)]
        return 1 - (together - alone) / alone if alone else 0.0

    def ask(self, determinant: Column, others: Sequence[Column]) -> None:
        """Asks for the counts of `determinant` alone, and together with `others`."""
        for expression in (
            self._expression(determinant, ()),
            self._expression(determinant, others),
        ):
            if expression not in self._counted and expression not in self._asked:
                self._asked.append(expression)

    def count(self) -> None:
        """Counts what was asked for since, `_PER_QUERY` at most in a query.

        Raises:
            SourceError: The database fails to count them.
        """
        dialect = self._source.dialect
        step = f"verifying the column dependencies of {self._source.name(self._table.name)}"
        for start in range(0, len(self._asked), _PER_QUERY):
            batch = self._asked[start : start + _PER_QUERY]
            (row,) = self._source.query(dialect.select(batch, self._table.name), step)
            for expression, found in zip(batch, row, strict=True):
                self._counted[expression] = counted(found, self._table.name)
        self._asked.clear()

    def _expression(self, determinant: Column, others: Iterable[Column]) -> str:
        """The expression of the distinct values of `determinant` where filled, with `others`."""
        dialect = self._source.dialect
        filled = dialect.without(determinant.name, determinant.type, determinant.left_aside)
        return dialect.exactly_distinct([filled, *(dialect.column(o.name) for o in others)])


def _verified(source: Source, table: Table, found: Sequence[_Found]) -> list[ColumnDependency]:
    """Those of `found` that hold on the whole table, of the columns that do, as strictly."""
    counts = _Counts(source, table)
    # Of each dependency, the columns that follow from its first determinant, while they do.
    following = [[*one.determinants[1:], *one.dependents] for one in found]
    for dependency, others in zip(found, following, strict=True):
        first, *equivalent = dependency.determinants
        counts.ask(first, others)
        for column in equivalent:
            counts.ask(column, [first])
    counts.count()
    falling = [
        index
        for index, (dependency, others) in enumerate(zip(found, following, strict=True))
        if counts.strictness(dependency.determinants[0], others) < _STRICTNESS
    ]
    for index in falling:
        for column in following[index]:
            counts.ask(found[index].determinants[0], [column])
    counts.count()
    for index in falling:
        first = found[index].determinants[0]
        following[index] = [
            c for c in following[index] if counts.strictness(first, [c]) >= _STRICTNESS
        ]
        counts.ask(first, following[index])
    counts.count()
    verified = []
    for dependency, others in zip(found, following, strict=True):
        first, *equivalent = dependency.determinants
        if not others:
            continue
        # An equivalent that does not determine the first is one of its dependents alone.
        names = {column.name for column in others}
        reverse = {
            column.name: counts.strictness(column, [first])
            for column in equivalent
            if column.name in names
        }
        determinants = [first.name, *(n for n, found in reverse.items() if found >= _STRICTNESS)]
        strictness = min(
            [counts.strictness(first, others), *(reverse[name] for name in determinants[1:])]
        )
        if strictness < _STRICTNESS:
            continue
        verified.append(
            ColumnDependency(
                determinants=tuple(determinants),
                dependents=tuple(
                    column.name
                    for column in table.columns
                    if column.name in names and column.name not in determinants
                ),
                strictness=round(strictness, DIGITS),
            )
        )
    return verified
