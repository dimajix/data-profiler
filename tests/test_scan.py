"""Tests of the stage scan, against the simulation environment, which has to run."""

import re
from pathlib import Path

from data_profiler.detect import SemanticType, Sensitivity
from data_profiler.profile import Match, Profile
from data_profiler.scan import scan
from data_profiler.source import Source
from data_profiler.workspace import Workspace

# How far the approximate number of distinct values may lie from the true one: four times the
# standard error the dialect asks for.
_TOLERANCE = 0.02


def test_a_scanned_profile_has_the_statistics_and_matches_its_tables_were_made_with(
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
            scanned_matches = {match.type: match for match in column.matches}
            for match in wanted.matches:
                assert scanned_matches.get(match.type) == match, (
                    f"{where}: its {match.type.value} is found again, in sample and on table"
                )


def test_the_semantic_types_of_the_columns_are_recognised_and_verified(
    source: Source, tmp_path: Path
) -> None:
    scanned = scan(source, re.compile("cust"), Workspace.open(tmp_path, "crm", "sales"))
    (table,) = scanned.tables
    matched = {column.name: column.matches for column in table.columns}
    assert matched["crt_dt"] == (Match(SemanticType.DATE, 1.0, 1.0),), "a date is a date as text"
    assert matched["upd_ts"] == (Match(SemanticType.DATE, 1.0, 1.0),), "nulls are not counted"
    assert matched["actv_flg"] == (), "a column of no type has no match"


def test_only_the_columns_of_no_sensitivity_have_their_values_in_the_profile(
    source: Source, tmp_path: Path
) -> None:
    scanned = scan(source, re.compile("cntct|cust"), Workspace.open(tmp_path, "crm", "sales"))
    columns = {
        f"{table.name}.{column.name}": column
        for table in scanned.tables
        for column in table.columns
    }
    assert columns["cust.cust_typ_cd"].values, "the values of an enumeration of no sensitivity"
    assert columns["cust.actv_flg"].values[0].value in ("true", "false"), "as the database writes"
    assert columns["cust.cust_nm"].statistics.range is not None, "a range of texts as well"
    for name in ("cntct.tel_no", "cntct.eml_adr"):
        assert columns[name].sensitivity is Sensitivity.PERSONAL, name
        assert columns[name].statistics.range is None, name
        assert columns[name].values == (), name


def test_only_the_tables_a_pattern_matches_whole_are_scanned(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    scanned = scan(source, re.compile("prod|ord"), workspace)
    assert [table.name for table in scanned.tables] == ["ord", "prod"]
    assert (scanned.catalog, scanned.schema) == (example.catalog, example.schema)
    sample = workspace.read_sample("prod")
    assert len(sample.columns["prod_id"]) == 350, "the sample of each table is in the workspace"
    enumerations = [enumeration.column for enumeration in workspace.read_enumerations("prod")]
    assert "prod_grp_cd" in enumerations, "the enumerations of each table are in the workspace"
