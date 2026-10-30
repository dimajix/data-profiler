"""The fixtures shared by the tests of the tool and those of the simulation."""

import sys
from collections.abc import Callable

import pytest


@pytest.fixture
def command_line(monkeypatch: pytest.MonkeyPatch) -> Callable[..., int]:
    """Runs the `main` of a command line with arguments, giving the exit code, 0 where it ends not.

    It is called as `command_line(main, *arguments)`.
    """

    def run(main: Callable[[], None], *arguments: str) -> int:
        monkeypatch.setattr(sys, "argv", [main.__module__, *arguments])
        try:
            main()
        except SystemExit as exit:
            return int(exit.code or 0)
        return 0

    return run
