"""The stage scan: what the selected tables of a source hold.

Each table is counted by the module `statistics`, by one query; the values of its enumerations are
counted by the module `enumerations`, and a sample of it is taken by the module `sampling`, both
into the workspace. The semantic types of its columns are recognised in the sample, and verified on
the whole table, by the module `matching`. No value of the database goes into the profile.
"""

import logging
from re import Pattern

from data_profiler.enumerations import values
from data_profiler.matching import recognise, verify
from data_profiler.profile import Profile
from data_profiler.sampling import take
from data_profiler.source import Source
from data_profiler.statistics import count
from data_profiler.workspace import Workspace

_logger = logging.getLogger(__name__)


def scan(source: Source, pattern: Pattern[str], workspace: Workspace) -> Profile:
    """The profile of the tables of `source` that `pattern` matches whole.

    Args:
        source: The schema whose tables are scanned.
        pattern: The names of the tables to scan, matched whole.
        workspace: Where the enumerations and the samples of the tables are kept.

    Returns:
        The profile: the tables, sorted by name, with their columns, types, statistics and
        matches.

    Raises:
        SourceError: The database fails to list the tables or their columns, to count one or the
            values of its enumerations, to take its sample, or to verify its matches.
        WorkspaceError: The enumerations or the sample of a table cannot be written.
    """
    tables = []
    for name in source.tables(pattern):
        _logger.info("Scanning %s", name)
        table = count(source, name)
        _logger.info("Scanned %s: %d rows, %d columns", name, table.rows, len(table.columns))
        workspace.write_enumerations(name, values(source, table))
        sample = take(source, table)
        workspace.write_sample(name, sample)
        tables.append(verify(source, recognise(table, sample)))
    return Profile(catalog=source.catalog, schema=source.schema, tables=tuple(tables))
