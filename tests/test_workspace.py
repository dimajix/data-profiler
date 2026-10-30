"""Tests of the workspace: kept out of version control, holding samples and enumerations."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from data_profiler.workspace import Enumeration, Sample, Workspace, WorkspaceError

_SAMPLE = Sample(
    columns={
        "id": [1, 2, 3],
        "nm": ["a", None, "c"],
        "amt": [Decimal("1.50"), Decimal("2.00"), None],
        "dt": [date(2026, 1, 1), None, date(2026, 1, 3)],
        "ts": [datetime(2026, 1, 1, 12), None, None],
        "flg": [True, False, None],
    }
)

_ENUMERATIONS = [
    Enumeration(column="cd", values=(("a", 3), ("b", 1))),
    Enumeration(column="amt", values=((Decimal("1.50"), 2), (Decimal("2.00"), 1))),
    Enumeration(column="dt", values=((date(2026, 1, 1), 5),)),
    Enumeration(column="flg", values=((True, 4), (False, 4))),
]


def test_a_workspace_keeps_itself_out_of_version_control(tmp_path: Path) -> None:
    Workspace.open(tmp_path / "work", "crm", "sales")
    ignored = (tmp_path / "work" / ".gitignore").read_text(encoding="utf-8")
    assert "*" in ignored.splitlines()


def test_a_gitignore_of_its_own_is_left_as_it_is(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("mine\n", encoding="utf-8")
    Workspace.open(tmp_path, "crm", "sales")
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "mine\n"


def test_a_sample_written_and_read_is_unchanged(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    workspace.write_sample("t", _SAMPLE)
    assert workspace.read_sample("t") == _SAMPLE


def test_enumerations_written_and_read_are_unchanged(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    workspace.write_enumerations("t", _ENUMERATIONS)
    assert workspace.read_enumerations("t") == _ENUMERATIONS


def test_enumerations_written_take_the_place_of_earlier_ones(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    workspace.write_enumerations("t", _ENUMERATIONS)
    workspace.write_enumerations("t", [])
    assert workspace.read_enumerations("t") == []


def test_enumerations_that_were_not_counted_are_named(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="holds no enumerations of t"):
        Workspace.open(tmp_path, "crm", "sales").read_enumerations("t")


def test_a_sample_that_was_not_taken_is_named(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="holds no sample of t"):
        Workspace.open(tmp_path, "crm", "sales").read_sample("t")


def test_a_workspace_that_cannot_be_made_is_refused(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="cannot be made"):
        Workspace.open(tmp_path / "file", "crm", "sales")


def test_a_sample_that_cannot_be_written_leaves_nothing_behind(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    (tmp_path / "samples" / "t.parquet").mkdir()
    with pytest.raises(WorkspaceError, match="cannot be written"):
        workspace.write_sample("t", _SAMPLE)
    assert [file.name for file in (tmp_path / "samples").iterdir()] == ["t.parquet"]


def test_a_sample_of_values_of_different_kinds_is_refused_without_naming_them(
    tmp_path: Path,
) -> None:
    sample = Sample(columns={"a": [1, "secret"]})
    with pytest.raises(WorkspaceError, match="values of different kinds") as raised:
        Workspace.open(tmp_path, "crm", "sales").write_sample("t", sample)
    assert "secret" not in str(raised.value), "a value of the database is not in the message"


def test_a_sample_that_is_no_parquet_cannot_be_read(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    (tmp_path / "samples" / "t.parquet").write_text("no parquet", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="cannot be read"):
        workspace.read_sample("t")


def test_enumerations_of_another_form_cannot_be_read(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path, "crm", "sales")
    workspace.write_sample("t", _SAMPLE)
    (tmp_path / "samples" / "t.parquet").rename(tmp_path / "enumerations" / "t.parquet")
    with pytest.raises(WorkspaceError, match="not of the form they are written in"):
        workspace.read_enumerations("t")


@pytest.mark.parametrize("table", ["../t", "a/b", ".hidden", ""])
def test_a_table_whose_name_would_leave_the_samples_is_refused(tmp_path: Path, table: str) -> None:
    with pytest.raises(WorkspaceError, match="no name of a file"):
        Workspace.open(tmp_path, "crm", "sales").write_sample(table, _SAMPLE)


def test_a_workspace_is_not_opened_for_another_schema(tmp_path: Path) -> None:
    Workspace.open(tmp_path, "crm", "sales")
    Workspace.open(tmp_path, "crm", "sales")
    with pytest.raises(WorkspaceError, match=r"is of crm\.sales, not of crm\.billing"):
        Workspace.open(tmp_path, "crm", "billing")
