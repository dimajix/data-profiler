"""The stage scan: what the selected tables of a source hold.

Each table is counted by the module `statistics`, by one query; the values of its enumerations are
counted by the module `enumerations`, and a sample of it is taken by the module `sampling`, both
into the workspace. The semantic types of its columns, those of the tool and those of the project,
are recognised in the sample, and verified on the whole table, by the module `matching`. The
overrides of the project mark its columns as they give, and which values of the database go into
the profile - the ranges and enumerations of the columns of no sensitivity -, the module
`disclosure` decides, by the same types and those marks.

The profile is written after every table, so that a scan that fails at one table keeps those before
it, each table with the run that counted it. A run that did not finish is resumed by the next scan,
which skips the tables the run counted, unless the overrides now mark their columns otherwise; a
run that finished is followed by a new one, which counts every table anew. Overrides that name a
table not selected are refused before anything is counted.

A scan updates the profile there is rather than replacing it: it drops the tables no longer
selected - deleted, or no longer matched by the pattern -, keeps the others until it counts them
anew, and keeps the glossary. A profile scanned with other semantic types loses its tables, as
their matches may name a type it no longer has; a profile of another schema, or one that cannot be
read, is refused rather than overwritten.
"""

import logging
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from re import Pattern

from data_profiler.detect import SemanticType
from data_profiler.disclosure import disclose
from data_profiler.enumerations import values
from data_profiler.matching import recognise, verify
from data_profiler.overrides import Overrides
from data_profiler.profile import Profile, Table, Value
from data_profiler.sampling import take
from data_profiler.source import Source, as_text
from data_profiler.statistics import count
from data_profiler.workspace import Enumeration, Workspace

_logger = logging.getLogger(__name__)


def scan(
    source: Source,
    pattern: Pattern[str],
    workspace: Workspace,
    types: tuple[SemanticType, ...],
    overrides: Overrides,
    directory: Path,
) -> None:
    """Scans the tables of `source` that `pattern` matches whole into the profile in `directory`.

    The profile is written after every table: each table with its columns, types, statistics and
    matches, marked as the overrides give, and the ranges and values of enumerations of the
    columns of no sensitivity; and the types of the project.

    Args:
        source: The schema whose tables are scanned.
        pattern: The names of the tables to scan, matched whole.
        workspace: Where the enumerations and the samples of the tables are kept.
        types: The semantic types of the project, recognised beside those of the tool.
        overrides: The overrides of the project, which mark the columns of the tables.
        directory: The directory of the profile, updated where there is one.

    Raises:
        SourceError: The database fails to list the tables or their columns, to count one or the
            values of its enumerations, to take its sample, or to verify its matches.
        WorkspaceError: The enumerations or the sample of a table cannot be written.
        OverridesError: The overrides name a table that is not selected, or a column its table
            does not have.
        ProfileError: The profile there is cannot be read, is of another schema, or the profile
            cannot be written.
    """
    started = datetime.now(UTC)
    profile = Profile.updating(directory, source.catalog, source.schema, types, started)
    names = source.tables(pattern)
    given = overrides.selected(names)
    profile = profile.restricted(names)
    profile.write(directory)
    for name in names:
        kept = profile.counted(name)
        if kept is not None and given[name].is_laid_over(kept):
            _logger.info("Skipping %s, counted by the run resumed", name)
            continue
        if kept is not None:
            _logger.info("Counting %s anew, as the overrides mark its columns otherwise", name)
        _logger.info("Scanning %s", name)
        table = count(source, name)
        _logger.info("Scanned %s: %d rows, %d columns", name, table.rows, len(table.columns))
        enumerations = values(source, table)
        workspace.write_enumerations(name, enumerations)
        sample = take(source, table)
        workspace.write_sample(name, sample)
        found = verify(source, recognise(table, sample, types))
        marked = given[name].laid_over(_valued(found, enumerations))
        profile = profile.updated(disclose(marked, types))
        profile.write(directory)
    profile.finished(datetime.now(UTC)).write(directory)


def _valued(table: Table, enumerations: Sequence[Enumeration]) -> Table:
    """`table`, each column of an enumeration with its values, as text, the most frequent first."""
    values = {enumeration.column: enumeration.values for enumeration in enumerations}
    columns = (
        replace(
            column,
            values=tuple(Value(as_text(value), rows) for value, rows in values[column.name]),
        )
        if column.name in values
        else column
        for column in table.columns
    )
    return replace(table, columns=tuple(columns))
