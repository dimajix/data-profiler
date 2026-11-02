"""The fixtures shared by the tests of the tool and those of the simulation."""

import sys
from collections.abc import Callable

import pytest

from data_profiler.detect import SemanticType, Sensitivity, project_type


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


@pytest.fixture
def account_number() -> SemanticType:
    """A semantic type of a project: an account number, `A` and ten digits, of personal data."""
    return project_type("account-number", Sensitivity.PERSONAL, "A[0-9]{10}")
