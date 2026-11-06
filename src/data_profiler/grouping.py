"""The column groups of a table: its columns filled together, found in its sample.

A column is filled in a row of the sample where it holds a value, neither null nor one of the
sentinels its statistics found. A column takes part where it is filled in enough rows of the sample
to be judged, `_FEWEST`, and in at most a share `_MOST` of them: columns filled in nearly every row
are filled in the same rows by chance - two filled at random in a share p of the rows have a
Jaccard index of p / (2 - p), which reaches 0.9 from p = 0.947 on -, and their nulls tell of them
already. Two columns are as similar as the Jaccard index of the rows they are filled in, and are
grouped by hierarchical clustering of complete linkage, cut at the distance `_DISTANCE`: every two
columns of a group are filled together in at least nine of ten of the rows either is filled in, so
that a group whose rows miss a member here and there is still one. A group holds two columns at
least. No query is needed: the sample holds the values of each column of a row at the same place.
"""

import logging
from collections.abc import Mapping
from dataclasses import replace
from itertools import combinations
from statistics import fmean
from typing import Final

from data_profiler.detect import is_filled
from data_profiler.profile import DIGITS, ColumnGroup, Table
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)

# The rows of the sample a column is to be filled in at least, and the share of them at most, to
# take part; the distance of two columns up to which they are grouped.
_FEWEST: Final = 10
_MOST: Final = 0.9
_DISTANCE: Final = 0.1


def group(table: Table, sample: Sample) -> Table:
    """`table` with the column groups of its columns filled together in `sample`.

    Args:
        table: The table, its columns with their statistics, which name their sentinels.
        sample: The sample of the table, with the values of each of its columns.

    Returns:
        The table with its column groups, in the order of their first columns, each with its columns
        in the order of the table; none where no columns are filled together.
    """
    names = []
    filled = []
    for column in table.columns:
        values = sample.columns[column.name]
        rows = frozenset(
            index for index, value in enumerate(values) if is_filled(value, column.left_aside)
        )
        if _FEWEST <= len(rows) <= _MOST * len(values):
            names.append(column.name)
            filled.append(rows)
    similar = {
        frozenset(pair): _jaccard(*(filled[member] for member in pair))
        for pair in combinations(range(len(filled)), 2)
    }
    groups = tuple(
        ColumnGroup(
            columns=tuple(names[member] for member in members),
            coherence=round(
                fmean(similar[frozenset(pair)] for pair in combinations(members, 2)), DIGITS
            ),
        )
        for members in _clusters(len(filled), similar)
        if len(members) > 1
    )
    _logger.info("Grouped the columns of %s: %d column groups", table.name, len(groups))
    return replace(table, column_groups=groups)


def _jaccard(first: frozenset[int], second: frozenset[int]) -> float:
    """The Jaccard index of the rows `first` and `second`: those of both, of those of either."""
    return len(first & second) / len(first | second)


def _clusters(count: int, similar: Mapping[frozenset[int], float]) -> list[list[int]]:
    """The clusters of `count` columns by complete linkage, up to `_DISTANCE`, in their order.

    `similar` gives the Jaccard index of each two columns. The two clusters merged next are those
    whose least similar columns are the most similar, the first such two where several are; the
    clusters keep the order of their first columns, and each its columns in their order.
    """
    clusters = [[member] for member in range(count)]
    while len(clusters) > 1:
        linkage = {
            (first, second): min(
                similar[frozenset((a, b))] for a in clusters[first] for b in clusters[second]
            )
            for first, second in combinations(range(len(clusters)), 2)
        }
        (first, second), closest = max(linkage.items(), key=lambda found: found[1])
        if closest < 1 - _DISTANCE:
            break
        clusters[first] = sorted([*clusters[first], *clusters.pop(second)])
    return clusters
