"""Samples of tables, taken at random by a query built from the building blocks of the dialect.

A sample holds about as many rows as `_SIZE`: the share of the rows that is taken is computed from
the rows the statistics counted, and a limit caps the rows the share happens to give. A table of
fewer rows is taken whole. The values of a sample are values of the database; they go into the
workspace alone, never into the profile or the log.
"""

import logging
from typing import Final

from data_profiler.profile import Table
from data_profiler.source import Source
from data_profiler.workspace import Sample

_logger = logging.getLogger(__name__)

# The rows a sample is to hold.
_SIZE: Final = 10_000


def take(source: Source, table: Table) -> Sample:
    """A sample of `table` of `source`, of about 10,000 rows taken at random.

    Args:
        source: The schema the table is in.
        table: The table, with its rows counted and its columns.

    Returns:
        The sample: the values of each column, by its name, in the order of the table.

    Raises:
        SourceError: The database fails to take the sample.
    """
    dialect = source.dialect
    names = [column.name for column in table.columns]
    percent = 100.0 if table.rows <= _SIZE else 100.0 * _SIZE / table.rows
    statement = dialect.sampled(
        [dialect.column(name) for name in names], table.name, percent, _SIZE
    )
    rows = source.query(statement, f"taking a sample of {source.name(table.name)}")
    _logger.info("Took a sample of %s: %d rows", table.name, len(rows))
    return Sample(columns={name: [row[index] for row in rows] for index, name in enumerate(names)})
