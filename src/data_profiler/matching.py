"""The matches of a table: its semantic types, recognised in its sample, verified on the table.

The types of each column are recognised in the values of the sample by the module `detect`; a type
is a match of the column where it is recognised in half of the values of the sample that are not
null, or more - a low share, as more hypotheses are better than fewer. The matches are verified on
the whole table by one query, built from the building blocks of the dialect, which counts the
values of each column that are not null and those the pattern of each detector matches; what a
detector checks beyond its pattern, SQL does not, so that the share on the table is at least the
one the check would give. A share is written with as many digits as a sample says.
"""

import logging
from dataclasses import replace
from typing import Final

from data_profiler.detect import detect
from data_profiler.profile import Match, Table
from data_profiler.source import Source, counted
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


def verify(source: Source, table: Table) -> Table:
    """`table`, each match of its columns with the share of the whole table its pattern matches.

    Args:
        source: The schema the table is in.
        table: The table, its rows counted and its columns with their statistics and matches.

    Returns:
        The table, each match of its columns verified; with no query where it has no match.

    Raises:
        SourceError: The database fails to count the values the patterns match.
    """
    dialect = source.dialect
    asked = [column for column in table.columns if column.matches]
    if not asked:
        return table
    # The values that are not null are counted by the same query, so that a table written to
    # since its statistics were counted gives no share above 1.
    expressions = [dialect.rows()]
    for column in asked:
        expressions.append(dialect.nulls(column.name))
        expressions += [
            dialect.matching(column.name, match.type.detector.pattern.pattern)
            for match in column.matches
        ]
    statement = dialect.select(expressions, table.name)
    (row,) = source.query(statement, f"verifying the matches of {source.name(table.name)}")
    values = iter(row)
    rows = counted(next(values), table.name)
    verified = {}
    for column in asked:
        where = f"{table.name}.{column.name}"
        present = rows - counted(next(values), where)
        matches = []
        for match in column.matches:
            matched = counted(next(values), where)
            share = round(matched / present, _DIGITS) if present else 0.0
            matches.append(replace(match, table=share))
        verified[column.name] = replace(column, matches=tuple(matches))
    columns = tuple(verified.get(column.name, column) for column in table.columns)
    _logger.info("Verified the matches of %s on the whole table", table.name)
    return replace(table, columns=columns)
