"""Tests of the stage scan, against the simulation environment, which has to run."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.detect import DATE, Detector, SemanticType, Sensitivity
from data_profiler.overrides import (
    ColumnOverride,
    DiscriminatorOverride,
    EntityOverride,
    Overrides,
    OverridesError,
    TableOverride,
)
from data_profiler.profile import Concept, Match, PrimaryKey, Profile, ProfileError, Table
from data_profiler.scan import scan
from data_profiler.source import Source
from data_profiler.workspace import Workspace, WorkspaceError

# How far the approximate number of distinct values may lie from the true one: as many times the
# standard error the dialect counts them with.
_ERRORS = 4
# A glossary of one concept, as a profile scanned before has it.
_GLOSSARY = {"customer": Concept(("cust",), "A person or company that buys.")}
# How far the coherence of a group, found in a sample, may lie from the one it was made with.
_COHERENCE = 0.01


def _scanned(
    source: Source,
    pattern: str,
    tmp_path: Path,
    types: tuple[SemanticType, ...] = (),
    overrides: Overrides = Overrides(),  # noqa: B008  # frozen, so that no call changes it
) -> Profile:
    """The profile of the tables `pattern` matches, scanned into `tmp_path` as `scan` is given."""
    workspace = _workspace(tmp_path)
    scan(source, re.compile(pattern), workspace, types, overrides, tmp_path / "profile")
    return Profile.read(tmp_path / "profile")


def _marked(table: str, column: str) -> Overrides:
    """Overrides that mark the column `column` of `table` as personal data."""
    given = TableOverride(columns={column: ColumnOverride(sensitivity=Sensitivity.PERSONAL)})
    return Overrides(tables={table: given})


def _workspace(tmp_path: Path) -> Workspace:
    """The workspace of a scan into `tmp_path`."""
    return Workspace.open(tmp_path / "workspace", "crm", "sales")


def _failing_at(tmp_path: Path, table: str) -> None:
    """Makes the sample of `table` in the workspace of `tmp_path` one that cannot be written."""
    (tmp_path / "workspace" / "samples" / f"{table}.parquet").mkdir(parents=True)


def test_a_scanned_profile_has_the_statistics_matches_keys_groups_and_entities_it_was_made_with(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    scanned = _scanned(source, ".*", tmp_path)
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
            assert found.sentinels == statistics.sentinels, where
            assert found.lengths == statistics.lengths, where
            tolerance = _ERRORS * source.dialect.distinct_error() * statistics.distinct
            assert abs(found.distinct - statistics.distinct) <= tolerance, (
                f"{where}: {found.distinct} distinct values, made with {statistics.distinct}"
            )
            scanned_matches = {match.type: match for match in column.matches}
            for match in wanted.matches:
                assert scanned_matches.get(match.type) == match, (
                    f"{where}: its {match.type.name} is found again, in sample and on table"
                )
        assert table.discriminator == expected.discriminator, f"{table.name}: its entities"
        # Random values make keys of two columns by chance as well, which the table holds.
        assert set(expected.keys) <= set(table.keys), f"{table.name}: its keys"
        assert table.primary_key == expected.primary_key, f"{table.name}: its primary key"
        assert [g.columns for g in table.column_groups] == [
            g.columns for g in expected.column_groups
        ], table.name
        for group, given in zip(table.column_groups, expected.column_groups, strict=True):
            assert abs(group.coherence - given.coherence) <= _COHERENCE, (
                f"{table.name}: {group.columns} of {group.coherence}, made with {given.coherence}"
            )


def test_the_semantic_types_of_the_columns_are_recognised_and_verified(
    source: Source, tmp_path: Path
) -> None:
    scanned = _scanned(source, "cust", tmp_path)
    (table,) = scanned.tables
    matched = {column.name: column.matches for column in table.columns}
    assert matched["crt_dt"] == (Match(DATE, 1.0, 1.0),), "a date is a date as text"
    assert matched["upd_ts"] == (Match(DATE, 1.0, 1.0),), "nulls are not counted"
    assert matched["cust_typ_cd"] == (), "a column of no type has no match"


def test_only_the_columns_of_no_sensitivity_have_their_values_in_the_profile(
    source: Source, tmp_path: Path
) -> None:
    scanned = _scanned(source, "cntct|cust", tmp_path)
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


def test_a_column_the_overrides_mark_sensitive_is_marked_without_its_values(
    source: Source, tmp_path: Path
) -> None:
    scanned = _scanned(source, "cust", tmp_path, overrides=_marked("cust", "cust_nm"))
    (table,) = scanned.tables
    (column,) = [column for column in table.columns if column.name == "cust_nm"]
    assert column.marked is Sensitivity.PERSONAL
    assert (column.statistics.range, column.values) == (None, ())


def test_a_column_without_sentinels_counts_what_the_tool_takes_for_them_as_values(
    source: Source, tmp_path: Path
) -> None:
    given = TableOverride(columns={"dlvr_pst_cd": ColumnOverride(sentinels=())})
    scanned = _scanned(source, "ord", tmp_path, overrides=Overrides(tables={"ord": given}))
    (table,) = scanned.tables
    (column,) = [column for column in table.columns if column.name == "dlvr_pst_cd"]
    assert column.sentinels == ()
    assert column.statistics.sentinels == ()
    assert column.matches == (), "its empty texts are values, of no type"


def test_overrides_of_a_table_not_selected_are_refused_before_anything_is_counted(
    source: Source, tmp_path: Path
) -> None:
    with pytest.raises(OverridesError, match="tables that are not profiled: prod"):
        _scanned(source, "cust", tmp_path, overrides=_marked("prod", "prod_nm"))
    assert not (tmp_path / "profile").exists()
    assert not (tmp_path / "workspace" / "samples" / "cust.parquet").exists()


def test_overrides_of_a_column_the_table_does_not_have_are_refused_keeping_the_tables_before(
    source: Source, tmp_path: Path
) -> None:
    with pytest.raises(OverridesError, match="columns of prod it does not have: gone"):
        _scanned(source, "cust|prod", tmp_path, overrides=_marked("prod", "gone"))
    (cust,) = Profile.read(tmp_path / "profile").tables
    assert cust.name == "cust", "the table before is written"


def test_only_the_tables_a_pattern_matches_whole_are_scanned(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    scanned = _scanned(source, "prod|ord", tmp_path)
    workspace = _workspace(tmp_path)
    assert [table.name for table in scanned.tables] == ["ord", "prod"]
    assert (scanned.catalog, scanned.schema) == (example.catalog, example.schema)
    sample = workspace.read_sample("prod")
    assert len(sample.columns["prod_id"]) == 350, "the sample of each table is in the workspace"
    enumerations = [enumeration.column for enumeration in workspace.read_enumerations("prod")]
    assert "prod_grp_cd" in enumerations, "the enumerations of each table are in the workspace"


def test_a_semantic_type_of_the_project_is_recognised_verified_and_kept_sensitive(
    source: Source, tmp_path: Path
) -> None:
    # The numbers of orders of the simulation are fourteen letters in lower case.
    order = SemanticType("order-number", Sensitivity.PERSONAL, Detector(re.compile("[a-z]{14}")))
    scanned = _scanned(source, "ord", tmp_path, (order,))
    assert scanned.types == (order,), "the profile holds the types of its project"
    (table,) = scanned.tables
    (column,) = [column for column in table.columns if column.name == "ord_no"]
    assert column.matches == (Match(order, 1.0, 1.0),)
    assert column.sensitivity is Sensitivity.PERSONAL
    assert (column.statistics.range, column.values) == (None, ())


def test_a_scan_that_fails_at_a_table_keeps_those_before_and_the_tables_it_had(
    source: Source, example_profile: Profile, tmp_path: Path
) -> None:
    (prod,) = [table for table in example_profile.tables if table.name == "prod"]
    Profile(catalog="crm", schema="sales", tables=(prod,)).write(tmp_path / "profile")
    _failing_at(tmp_path, "prod")
    with pytest.raises(WorkspaceError):
        _scanned(source, "cust|prod", tmp_path)
    cust, kept = Profile.read(tmp_path / "profile").tables
    assert cust.name == "cust", "the table before the failure is written"
    assert kept == prod, "a table is kept until it is counted anew"


def test_a_scan_keeps_the_glossary_and_drops_the_tables_no_longer_selected(
    source: Source, tmp_path: Path
) -> None:
    gone = Table(name="gone", rows=0, columns=())
    Profile(catalog="crm", schema="sales", tables=(gone,), glossary=_GLOSSARY).write(
        tmp_path / "profile"
    )
    scanned = _scanned(source, "cust", tmp_path)
    assert [table.name for table in scanned.tables] == ["cust"]
    assert scanned.glossary == _GLOSSARY
    assert not (tmp_path / "profile" / "tables" / "gone.yml").exists()


def test_a_profile_scanned_with_other_types_keeps_its_tables_until_they_are_counted_anew(
    source: Source, example_profile: Profile, account_number: SemanticType, tmp_path: Path
) -> None:
    Profile(
        catalog="crm",
        schema="sales",
        tables=example_profile.tables,
        glossary=_GLOSSARY,
        types=(account_number,),
    ).write(tmp_path / "profile")
    _failing_at(tmp_path, "prod")
    with pytest.raises(WorkspaceError):
        _scanned(source, "cust|prod", tmp_path)
    profile = Profile.read(tmp_path / "profile")
    cust, prod = profile.tables
    assert profile.types == ()
    assert profile.glossary == _GLOSSARY, "the glossary is kept all the same"
    assert any(column.matches for column in cust.columns), "a table counted anew"
    assert not any(column.matches or column.values for column in prod.columns), (
        "a table not counted anew, without its matches and values"
    )


def test_a_profile_that_cannot_be_read_is_refused_not_overwritten(
    source: Source, tmp_path: Path
) -> None:
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "profile.yml").write_text("format: 5\n", encoding="utf-8")
    with pytest.raises(ProfileError, match="of another major version"):
        _scanned(source, "cust", tmp_path)
    assert (tmp_path / "profile" / "profile.yml").read_text(encoding="utf-8") == "format: 5\n"


def test_a_run_that_failed_is_resumed_counting_only_the_tables_it_did_not(
    source: Source, tmp_path: Path
) -> None:
    _failing_at(tmp_path, "prod")
    with pytest.raises(WorkspaceError):
        _scanned(source, "cust|prod", tmp_path)
    failed = Profile.read(tmp_path / "profile")
    assert failed.run is not None
    assert failed.run.finished is None, "a run that failed did not finish"
    (cust,) = failed.tables
    # Its rows told apart from those a scan counts, to see that it is not counted again.
    failed.updated(replace(cust, rows=-1)).write(tmp_path / "profile")
    (tmp_path / "workspace" / "samples" / "prod.parquet").rmdir()
    resumed = _scanned(source, "cust|prod", tmp_path)
    assert [table.rows for table in resumed.tables if table.name == "cust"] == [-1]
    assert [table.name for table in resumed.tables] == ["cust", "prod"]
    assert resumed.run is not None
    assert resumed.run.started == failed.run.started, "the same run"
    assert resumed.run.finished is not None
    assert all(table.run == resumed.run.started for table in resumed.tables)


def test_a_run_resumed_counts_a_table_anew_whose_columns_the_overrides_mark_otherwise(
    source: Source, tmp_path: Path
) -> None:
    _failing_at(tmp_path, "prod")
    with pytest.raises(WorkspaceError):
        _scanned(source, "cust|prod", tmp_path)
    failed = Profile.read(tmp_path / "profile")
    (cust,) = failed.tables
    # Its rows told apart from those a scan counts, to see that it is counted again.
    failed.updated(replace(cust, rows=-1)).write(tmp_path / "profile")
    (tmp_path / "workspace" / "samples" / "prod.parquet").rmdir()
    resumed = _scanned(source, "cust|prod", tmp_path, overrides=_marked("cust", "cust_nm"))
    assert resumed.run is not None
    assert failed.run is not None
    assert resumed.run.started == failed.run.started, "the same run"
    table, _ = resumed.tables
    assert table.rows != -1, "counted anew"
    (column,) = [column for column in table.columns if column.name == "cust_nm"]
    assert (column.marked, column.statistics.range) == (Sensitivity.PERSONAL, None)


def test_a_run_resumed_counts_a_table_anew_whose_sentinels_the_overrides_give_otherwise(
    source: Source, tmp_path: Path
) -> None:
    _failing_at(tmp_path, "prod")
    with pytest.raises(WorkspaceError):
        _scanned(source, "ord|prod", tmp_path)
    failed = Profile.read(tmp_path / "profile")
    (ord,) = failed.tables
    # Its rows told apart from those a scan counts, to see that it is counted again.
    failed.updated(replace(ord, rows=-1)).write(tmp_path / "profile")
    (tmp_path / "workspace" / "samples" / "prod.parquet").rmdir()
    given = TableOverride(columns={"dlvr_pst_cd": ColumnOverride(sentinels=())})
    resumed = _scanned(source, "ord|prod", tmp_path, overrides=Overrides(tables={"ord": given}))
    table, _ = resumed.tables
    assert table.rows != -1, "counted anew"
    (column,) = [column for column in table.columns if column.name == "dlvr_pst_cd"]
    assert (column.sentinels, column.statistics.sentinels) == ((), ())


def test_a_run_resumed_counts_a_table_anew_whose_discriminator_the_overrides_give_otherwise(
    source: Source, tmp_path: Path
) -> None:
    scanned = _scanned(source, "prtnr", tmp_path)
    assert scanned.run is not None
    (prtnr,) = scanned.tables
    assert prtnr.discriminator is not None, "found"
    # A run that did not finish, its table told apart from those a scan counts.
    unfinished = replace(scanned, run=replace(scanned.run, finished=None))
    unfinished.updated(replace(prtnr, rows=-1)).write(tmp_path / "profile")
    given = Overrides(tables={"prtnr": TableOverride(discriminator=False)})
    (table,) = _scanned(source, "prtnr", tmp_path, overrides=given).tables
    assert table.rows != -1, "counted anew"
    assert table.discriminator is None, "none, as given"


def test_a_scan_tells_the_entities_apart_by_the_discriminator_the_overrides_give(
    source: Source, tmp_path: Path
) -> None:
    entities = {"customer": EntityOverride(("K",)), "other": EntityOverride(("KX",))}
    given = TableOverride(discriminator=DiscriminatorOverride("prtnr_typ_cd", entities))
    overrides = Overrides(tables={"prtnr": given})
    (table,) = _scanned(source, "prtnr", tmp_path, overrides=overrides).tables
    assert table.discriminator is not None
    assert table.discriminator.given == (("K",), ("KX",)), "the values given it was counted with"
    assert [entity.values for entity in table.discriminator.entities] == [
        ("K",),
        ("L", "LX"),
        ("I",),
        ("M",),
        ("KX",),
    ]
    assert given.agrees_with(table)


def test_a_scan_takes_the_primary_key_the_overrides_give(source: Source, tmp_path: Path) -> None:
    given = Overrides(tables={"ord_itm": TableOverride(primary_key=("pos_no", "ord_id"))})
    (table,) = _scanned(source, "ord_itm", tmp_path, overrides=given).tables
    assert table.primary_key == PrimaryKey(("ord_id", "pos_no"), given=True)
    assert ("ord_itm_id",) in table.keys, "the key it would have chosen among the keys"
    assert given.tables["ord_itm"].agrees_with(table)


def test_a_primary_key_given_of_no_columns_is_refused_before_it_is_verified(
    source: Source, tmp_path: Path
) -> None:
    given = Overrides(tables={"prod": TableOverride(primary_key=())})
    with pytest.raises(OverridesError, match="a primary key of prod of no columns"):
        _scanned(source, "prod", tmp_path, overrides=given)


def test_a_run_resumed_counts_a_table_anew_whose_primary_key_the_overrides_give_otherwise(
    source: Source, tmp_path: Path
) -> None:
    scanned = _scanned(source, "prod", tmp_path)
    assert scanned.run is not None
    (prod,) = scanned.tables
    # A run that did not finish, its table told apart from those a scan counts.
    unfinished = replace(scanned, run=replace(scanned.run, finished=None))
    unfinished.updated(replace(prod, rows=-1)).write(tmp_path / "profile")
    given = Overrides(tables={"prod": TableOverride(primary_key=("prod_cd",))})
    (table,) = _scanned(source, "prod", tmp_path, overrides=given).tables
    assert table.rows != -1, "counted anew"
    assert table.primary_key == PrimaryKey(("prod_cd",), given=True)


def test_a_run_that_finished_is_followed_by_a_new_one_counting_every_table(
    source: Source, tmp_path: Path
) -> None:
    first = _scanned(source, "cust", tmp_path)
    second = _scanned(source, "cust", tmp_path)
    assert first.run is not None
    assert second.run is not None
    assert second.run.started > first.run.started, "a new run"
    assert second.tables[0].run == second.run.started, "the table is counted anew"
