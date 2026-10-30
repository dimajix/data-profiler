"""Tests of the command line of the tool, on a copy of the example project."""

import logging
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from data_profiler.cli import main
from data_profiler.profile import Profile

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A copy of the example project, its `.env` holding the password of the simulation.

    The variables the command line reads from `.env` are kept to the test.
    """
    shutil.copy(_EXAMPLE / "project.yml", tmp_path)
    (tmp_path / ".env").write_text("SIMULATION_PASSWORD=profiler\n", encoding="utf-8")
    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.delenv("SIMULATION_PASSWORD", raising=False)
    return tmp_path


@pytest.mark.usefixtures("user_environment")
def test_an_environment_is_scanned_into_its_directory(
    project: Path, example: Profile, command_line: Callable[..., int]
) -> None:
    assert command_line(main, "scan", "simulation", "--project", str(project)) == 0
    scanned = Profile.read(project / "simulation" / "profile.yml")
    assert [table.name for table in scanned.tables] == sorted(t.name for t in example.tables)
    assert (project / "simulation" / "workspace" / "samples" / "cust.parquet").is_file()


def test_the_project_is_the_current_directory_if_none_is_given(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    command_line: Callable[..., int],
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.chdir(project)
    assert command_line(main, "scan", "prod") == 1
    assert caplog.messages[-1] == "project.yml has no environment prod; it has: simulation"


@pytest.mark.usefixtures("user_environment")
def test_the_password_is_not_logged_when_the_scan_fails(
    project: Path, command_line: Callable[..., int], caplog: pytest.LogCaptureFixture
) -> None:
    (project / ".env").write_text("SIMULATION_PASSWORD=not-the-password\n", encoding="utf-8")
    caplog.set_level(logging.DEBUG)
    assert command_line(main, "--debug", "scan", "simulation", "--project", str(project)) == 1
    assert caplog.records, "the failure is logged"
    assert "not-the-password" not in caplog.text
