"""Tests of the command line of the tool, on a copy of the example project."""

import logging
import os
import shutil
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from yaml import safe_dump

from data_profiler.cli import main
from data_profiler.detect import Sensitivity
from data_profiler.glossary import occurrences
from data_profiler.profile import Concept, Profile

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
    # The numbers of orders of the simulation are fourteen letters in lower case.
    with (project / "project.yml").open("a", encoding="utf-8") as file:
        file.write("types:\n  order-number: {pattern: '[a-z]{14}', sensitivity: personal}\n")
    shutil.copy(_EXAMPLE / "overrides.yml", project)
    assert command_line(main, "scan", "simulation", "--project", str(project)) == 0
    scanned = Profile.read(project / "simulation" / "profile")
    assert [table.name for table in scanned.tables] == sorted(t.name for t in example.tables)
    assert [kind.name for kind in scanned.types] == ["order-number"], "of project.yml"
    marked = [c for t in scanned.tables for c in t.columns if c.marked is Sensitivity.PERSONAL]
    assert sorted(c.name for c in marked) == ["ap_ap_nm", "cust_nm", "frst_nm", "lst_nm"], (
        "of overrides.yml"
    )
    given = [c for t in scanned.tables for c in t.columns if c.sentinels is not None]
    assert [(c.name, c.sentinels) for c in given] == [("dlvr_pst_cd", ("", "00000"))]
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


def test_the_profile_of_an_environment_is_reported_with_the_overrides_laid_over(
    project: Path, example_profile: Profile, command_line: Callable[..., int]
) -> None:
    shutil.copy(_EXAMPLE / "overrides.yml", project)
    (project / "simulation").mkdir()
    example_profile.write(project / "simulation" / "profile")
    assert command_line(main, "report", "simulation", "--project", str(project)) == 0
    page = (project / "simulation" / "report.html").read_text(encoding="utf-8")
    assert "<h1>crm.sales</h1>" in page
    assert "personal (marked)" in page, "the overrides of the project are laid over"


def test_the_profile_of_an_environment_is_described_into_its_directory(
    project: Path, example_profile: Profile, command_line: Callable[..., int]
) -> None:
    # Every term of a concept given, and every column a description, so that the language model
    # is asked nothing.
    given = {f"word_{term}": {"abbreviations": [term]} for term in occurrences(example_profile)}
    descriptions = {
        table.name: {"columns": {c.name: {"description": "Given."} for c in table.columns}}
        for table in example_profile.tables
    }
    document = {"format": 6, "glossary": given, "tables": descriptions}
    (project / "overrides.yml").write_text(safe_dump(document), encoding="utf-8")
    (project / "simulation").mkdir()
    proposed = {"customer": Concept(("cust",))}
    replace(example_profile, glossary=proposed).write(project / "simulation" / "profile")
    assert command_line(main, "describe", "simulation", "--project", str(project)) == 0
    described = Profile.read(project / "simulation" / "profile")
    assert all(column.reading is not None for t in described.tables for column in t.columns)
    assert described.glossary == proposed, "nothing of the overrides, and the concepts proposed"
    arguments = ("describe", "simulation", "--project", str(project), "--anew")
    assert command_line(main, *arguments) == 0
    assert Profile.read(project / "simulation" / "profile").glossary == {}, "dropped first"


def test_the_profile_of_an_environment_is_described_without_a_language_model(
    project: Path, example_profile: Profile, command_line: Callable[..., int]
) -> None:
    configuration = (project / "project.yml").read_text(encoding="utf-8")
    without = "".join(line for line in configuration.splitlines(True) if "llm" not in line)
    (project / "project.yml").write_text(without, encoding="utf-8")
    (table, *others) = example_profile.tables
    described = replace(table, columns=(replace(table.columns[0], description="Proposed."),))
    proposed = replace(
        example_profile, tables=(described, *others), glossary={"x": Concept(("x",))}
    )
    proposed.write(project / "simulation" / "profile")
    arguments = ("describe", "simulation", "--project", str(project), "--without-llm")
    assert command_line(main, *arguments) == 0, "though the project names no language model"
    profile = Profile.read(project / "simulation" / "profile")
    assert all(column.terms is not None for t in profile.tables for column in t.columns), "split"
    assert profile.glossary == {}, "the concept of no term dropped, and none proposed"
    assert profile.tables[0].columns[0].description == "Proposed.", "kept"
    assert command_line(main, *arguments, "--anew") == 0, "both options together"
    profile = Profile.read(project / "simulation" / "profile")
    assert profile.tables[0].columns[0].description is None, "dropped first, and none proposed"


def test_the_profile_of_an_environment_is_reported_without_its_password(
    project: Path, example_profile: Profile, command_line: Callable[..., int]
) -> None:
    (project / ".env").unlink()
    (project / "simulation").mkdir()
    example_profile.write(project / "simulation" / "profile")
    assert command_line(main, "report", "simulation", "--project", str(project)) == 0
