"""The stage scan: what the selected tables of a source hold, counted on the whole tables.

Each table is counted by the module `statistics`, by one query. No value of the database goes into
the profile.
"""

import logging
from re import Pattern

from data_profiler.profile import Profile
from data_profiler.source import Source
from data_profiler.statistics import count

_logger = logging.getLogger(__name__)


def scan(source: Source, pattern: Pattern[str]) -> Profile:
    """The profile of the tables of `source` that `pattern` matches whole.

    Args:
        source: The schema whose tables are scanned.
        pattern: The names of the tables to scan, matched whole.

    Returns:
        The profile: the tables, sorted by name, with their columns, types and statistics.

    Raises:
        SourceError: The database fails to list the tables or their columns, or to count one.
    """
    tables = []
    for name in source.tables(pattern):
        _logger.info("Scanning %s", name)
        table = count(source, name)
        _logger.info("Scanned %s: %d rows, %d columns", name, table.rows, len(table.columns))
        tables.append(table)
    return Profile(catalog=source.catalog, schema=source.schema, tables=tuple(tables))
