"""The matches of a table: the semantic types of its columns, recognised in its sample.

The types of each column are recognised in the values of the sample by the module `detect`; a type
is a match of the column where it is recognised in half of the values of the sample that are not
null, or more - a low share, as more hypotheses are better than fewer. A share is written with as
many digits as a sample says.
"""

import logging
from dataclasses import replace
from typing import Final

from data_profiler.detect import detect
from data_profiler.profile import Match, Table
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)

# The share of the values of a sample a semantic type has to be recognised in, to be a match.
_MATCHING: Final = 0.5

# The digits a share is written with.
_DIGITS: Final = 3


def recognise(table: Table, sample: Sample) -> Table:
    """`table`, its columns with the semantic types recognised in `sample`, most frequent first.

    Args:
        table: The table, with its columns.
        sample: The sample of the table, with the values of each of its columns.

    Returns:
        The table, each of its columns with its matches.
    """
    columns = []
    for column in table.columns:
        shares = detect(sample.columns[column.name])
        matches = tuple(
            Match(type=kind, sample=round(share, _DIGITS))
            for kind, share in sorted(shares.items(), key=lambda found: -found[1])
            if share >= _MATCHING
        )
        columns.append(replace(column, matches=matches))
    found = sum(len(column.matches) for column in columns)
    _logger.info("Recognised the semantic types of %s: %d matches", table.name, found)
    return replace(table, columns=tuple(columns))
