"""Tests of the command line of the simulation, which needs the environment to run."""

import logging
import sys
from pathlib import Path

import pytest

from data_profiler.profile import Profile
from simulation.cli import main

_EXAMPLE = Path(__file__).parents[1] / "profiles" / "crm.yml"


def _run(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> int:
    """The exit code of the command line run with `arguments`, 0 where it does not exit."""
    monkeypatch.setattr(sys, "argv", ["simulation", *arguments])
    try:
        main()
    except SystemExit as exit:
        return int(exit.code or 0)
    return 0


def test_a_profile_is_loaded_and_its_tables_counted(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    assert _run(monkeypatch, "load", str(_EXAMPLE)) == 0
    assert "Trino counts sales.ord_itm: 61000 rows" in caplog.messages


def test_a_failed_load_ends_with_its_message_and_exit_code_1(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    path = tmp_path / "profile.yml"
    Profile(catalog="billing", schema="sales", tables=()).write(path)
    assert _run(monkeypatch, "load", str(path)) == 1
    assert caplog.messages[-1].startswith("the profile is of the catalog billing")
