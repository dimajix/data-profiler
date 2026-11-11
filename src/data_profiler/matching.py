"""The matches of a table: its semantic types, recognised in its sample, verified on the table.

The types of each column are recognised in the values of the sample by the module `detect`, which
makes a type a match of the column where the share of the values of the sample that are neither
null nor sentinels it is recognised in reaches the threshold of its detector. The matches are
verified on the whole table by one query, built from the building blocks of the dialect, which
counts the values of each column that are neither null nor sentinels and those the pattern of each
detector matches. The sentinels of a column are left aside where its statistics counted any. What
a detector checks of a value beyond its pattern, SQL does not, so that the share on the table is at
least the one the check would give, and a condition of the column is judged on the sample alone. A
share is written with as many digits as a sample says.
"""

import logging
from collections.abc import Sequence
from dataclasses import replace

from data_profiler.detect import SemanticType, detect
from data_profiler.profile import DIGITS, Match, Table
from data_profiler.source import Source
from data_profiler.values import counted
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)


def recognise(table: Table, sample: Sample, types: Sequence[SemanticType]) -> Table:
    """`table`, its columns with the semantic types recognised in `sample`, most frequent first.

    Args:
        table: The table, with its columns and their statistics.
        sample: The sample of the table, with the values of each of its columns.
        types: The semantic types of the project, recognised beside those of the tool.

    Returns:
        The table, each of its columns with its matches.
    """
    columns = []
    for column in table.columns:
        shares = detect(sample.columns[column.name], types, column.left_aside)
        matches = tuple(
            Match(type=kind, sample=round(share, DIGITS))
            for kind, share in sorted(shares.items(), key=lambda found: -found[1])
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
        The table, each match of its columns verified, but of those of no text; with no query
        where it has no match of a column of text.

    Raises:
        SourceError: The database fails to count the values the patterns match.
    """
    dialect = source.dialect
    # A pattern is tried on no values of a column of no text: its matches stay unverified.
    asked = [c for c in table.columns if c.matches and dialect.has_text(c.type)]
    if not asked:
        return table
    # The values that are neither null nor sentinels are counted by the same query, so that a table
    # written to since its statistics were counted gives no share above 1.
    expressions = [dialect.rows()]
    for column in asked:
        values = dialect.without(column.name, column.type, column.left_aside)
        expressions.append(dialect.nulls(values))
        expressions += [
            dialect.matching(values, match.type.detector.pattern.pattern)
            for match in column.matches
        ]
    statement = dialect.select(expressions, table.name)
    (row,) = source.query(statement, f"verifying the matches of {source.name(table.name)}")
    answers = iter(row)
    rows = counted(next(answers), table.name)
    verified = {}
    for column in asked:
        where = f"{table.name}.{column.name}"
        filled = rows - counted(next(answers), where)
        matches = []
        for match in column.matches:
            matched = counted(next(answers), where)
            share = round(matched / filled, DIGITS) if filled else 0.0
            matches.append(replace(match, table=share))
        verified[column.name] = replace(column, matches=tuple(matches))
    columns = tuple(verified.get(column.name, column) for column in table.columns)
    _logger.info("Verified the matches of %s on the whole table", source.name(table.name))
    return replace(table, columns=columns)
