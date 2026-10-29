"""Tests of the stage scan, against the simulation environment, which has to run."""

import re
from pathlib import Path

from data_profiler.profile import Profile
from data_profiler.scan import scan
from data_profiler.source import Source
from data_profiler.workspace import Workspace

# How far the approximate number of distinct values may lie from the true one: four times the
# standard error the dialect asks for.
_TOLERANCE = 0.02


def test_a_scanned_profile_has_the_statistics_its_tables_were_made_with(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    scanned = scan(source, re.compile(".*"), Workspace.open(tmp_path, "crm", "sales"))
    made = {table.name: table for table in example.tables}
    assert [table.name for table in scanned.tables] == sorted(made)
    for table in scanned.tables:
        expected = made[table.name]
        assert table.rows == expected.rows, table.name
        assert [(c.name, c.type) for c in table.columns] == [
            (c.name, c.type) for c in expected.columns
        ], table.name
        for column, wanted in zip(table.columns, expected.columns, strict=True):
            found, statistics = column.statistics, wanted.statistics
            where = f"{table.name}.{column.name}"
            assert found.nulls == statistics.nulls, where
            assert found.lengths == statistics.lengths, where
            assert abs(found.distinct - statistics.distinct) <= _TOLERANCE * statistics.distinct, (
                f"{where}: {found.distinct} distinct values, made with {statistics.distinct}"
            )


def test_only_the_tables_a_pattern_matches_whole_are_scanned(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    scanned = scan(source, re.compile("prod|ord"), workspace)
    assert [table.name for table in scanned.tables] == ["ord", "prod"]
    assert (scanned.catalog, scanned.schema) == (example.catalog, example.schema)
    sample = workspace.read_sample("prod")
    assert len(sample.columns["prod_id"]) == 350, "the sample of each table is in the workspace"
