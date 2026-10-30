"""Tests of the command line of the simulation, which needs the environment to run."""

import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from data_profiler.profile import Profile
from simulation.cli import main

_EXAMPLE = Path(__file__).parents[1] / "profiles" / "crm.yml"


def test_a_profile_is_loaded_and_its_tables_counted(
    command_line: Callable[..., int], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    assert command_line(main, "load", str(_EXAMPLE)) == 0
    assert "Trino counts sales.ord_itm: 61000 rows" in caplog.messages


def test_a_failed_load_ends_with_its_message_and_exit_code_1(
    command_line: Callable[..., int], caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    path = tmp_path / "profile.yml"
    Profile(catalog="billing", schema="sales", tables=()).write(path)
    assert command_line(main, "load", str(path)) == 1
    assert caplog.messages[-1].startswith("the profile is of the catalog billing")
