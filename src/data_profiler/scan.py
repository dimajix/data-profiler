"""The stage scan: what the selected tables of a source hold.

Each table is counted by the module `statistics`, by one query, its columns with the sentinels the
overrides of the project give of them, or else those of the tool; the values of its enumerations are
counted by the module `enumerations`, and a sample of it is taken by the module `sampling`, both
into the workspace. The semantic types of its columns, those of the tool and those of the project,
are recognised in the sample, and verified on the whole table, by the module `matching`; its keys
are indicated by the statistics and the sample, and verified on the whole table, by the module
`keys`; the columns filled together are found in the sample, by the module `grouping`, and the
columns whose values follow from another are found in the sample and verified on the whole table, by
the module `dependencies`, of no determinant the overrides give as determining none. Its columns of
lists are found in the sample, by the module `lists`, of the separator the overrides give of the
table, else that of the project. The overrides of the project mark its columns as they give, and
which values of the database go into the profile - the ranges and enumerations of the columns of no
sensitivity -, the module `disclosure` decides, by the same types and those marks. Of the
enumerations the profile holds, the module `entities` finds the discriminator whose values tell the
entities of the rows apart, by a query of its own, or takes the one the overrides give.

The profile is written after every table, so that a scan that fails at one table keeps those before
it, each table with the run that counted it. A run that did not finish is resumed by the next scan,
which skips the tables the run counted, unless the overrides now give their columns, their primary
keys or their discriminators otherwise, or their columns of lists are of another separator; a run
that finished is followed by a new one, which counts every table anew. Overrides that name a table
not selected are refused before anything is counted.

A scan updates the profile there is rather than replacing it: it drops the tables no longer
selected, deleted or no longer matched by the pattern, keeps the others until it counts them anew,
and keeps what the other stages filled: the glossary, the terms and readings of the names of the
tables and columns that stay, and the descriptions of those columns; the references and reference
candidates of a table it counts anew are dropped, until relate runs again. A profile scanned with
other semantic types keeps its tables without their matches, which may name a type it no longer
has, and the values and ranges of their columns, until it counts them anew; a profile of another
schema, or one that cannot be read, is refused rather than overwritten.
"""

import logging
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from re import Pattern

from data_profiler.dependencies import determine
from data_profiler.detect import SemanticType
from data_profiler.disclosure import disclose
from data_profiler.entities import discriminate
from data_profiler.enumerations import values
from data_profiler.grouping import group
from data_profiler.keys import identify
from data_profiler.lists import is_listed_with, listed
from data_profiler.matching import recognise, verify
from data_profiler.overrides import Overrides
from data_profiler.profile import Profile, Table, Value
from data_profiler.sampling import take
from data_profiler.source import Source
from data_profiler.statistics import count
from data_profiler.values import as_text
from data_profiler.workspace import Enumeration, Workspace

_logger = logging.getLogger(__name__)


def scan(
    source: Source,
    pattern: Pattern[str],
    workspace: Workspace,
    types: tuple[SemanticType, ...],
    list_separator: str | None,
    overrides: Overrides,
    directory: Path,
) -> None:
    """Scans the tables of `source` that `pattern` matches whole into the profile in `directory`.

    The profile is written after every table: each table with its columns, types, statistics and
    matches, its columns of lists, marked as the overrides give, its keys and primary key, the
    column groups of its columns filled together, the column dependencies of its columns, the
    discriminator of its entities, and the ranges and values of enumerations of the columns of no
    sensitivity; and the types of the project.

    Args:
        source: The schema whose tables are scanned.
        pattern: The names of the tables to scan, matched whole.
        workspace: Where the enumerations and the samples of the tables are kept.
        types: The semantic types of the project, recognised beside those of the tool.
        list_separator: The separator of the values of a list in a text, of the project, or None
            where it gives none.
        overrides: The overrides of the project, which mark the columns of the tables and give
            their sentinels, primary keys, columns determining none, discriminators and
            separators of lists.
        directory: The directory of the profile, updated where there is one.

    Raises:
        SourceError: The database fails to list the tables or their columns, to count one or the
            values of its enumerations, to take its sample, to verify its matches, its keys or its
            column dependencies, or to count the rows of its entities.
        WorkspaceError: The enumerations or the sample of a table cannot be written.
        OverridesError: The overrides name a table that is not selected, or a column its table
            does not have, or give sentinels of a column whose values are no text, or a primary
            key or a discriminator that cannot be one, as `TableOverride.laid_over` says.
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
        separator = given[name].list_separator or list_separator
        kept = profile.counted(name)
        if kept is not None and given[name].agrees_with(kept) and is_listed_with(kept, separator):
            _logger.info("Skipping %s, counted by the run resumed", name)
            continue
        if kept is not None:
            _logger.info(
                "Counting %s anew, as the overrides give its columns, primary key or"
                " discriminator otherwise, or its lists are of another separator",
                name,
            )
        _logger.info("Scanning %s", name)
        table = count(source, name, given[name].sentinels)
        given[name].refuse_uncounted(table)
        _logger.info("Scanned %s: %d rows, %d columns", name, table.rows, len(table.columns))
        enumerations = values(source, table)
        workspace.write_enumerations(name, enumerations)
        sample = take(source, table)
        workspace.write_sample(name, sample)
        verified = verify(source, recognise(listed(table, sample, separator), sample, types))
        keyed = identify(source, verified, sample, given[name].primary_key)
        found = determine(source, group(keyed, sample), sample, given[name].determining_none)
        marked = given[name].laid_over(_valued(found, enumerations))
        disclosed = disclose(marked, types)
        profile = profile.updated(discriminate(source, disclosed, given[name].discriminator))
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
