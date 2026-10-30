"""Tests of commands: their work run, and the program ended when it fails."""

import subprocess
import sys

from data_profiler.commands import run

# A command whose work fails with the error `{error}`, its log at debug level if `{debug}`.
_FAILING = """
from data_profiler.commands import run

class ShownError(Exception):
    pass

def fail():
    raise {error}

run(fail, debug={debug}, shown=(ShownError,))
"""


def _failed(error: str, debug: bool) -> subprocess.CompletedProcess[str]:
    """The command whose work fails with `error`, run as a program of its own."""
    program = _FAILING.format(error=error, debug=debug)
    return subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )


def test_work_that_succeeds_ends_nothing() -> None:
    done = []
    run(lambda: done.append(True), debug=False, shown=())
    assert done == [True]


def test_work_that_fails_shown_ends_with_its_message_and_exit_code_1() -> None:
    failed = _failed("ShownError('the table is gone')", debug=False)
    assert failed.returncode == 1
    assert failed.stderr == "ERROR the table is gone\n"


def test_work_that_fails_otherwise_ends_without_its_message_and_exit_code_1() -> None:
    failed = _failed("ValueError('the value 4111 1111')", debug=False)
    assert failed.returncode == 1
    assert (
        failed.stderr == "ERROR The command failed unexpectedly; with --debug, the log says why.\n"
    )


def test_the_log_of_work_that_fails_holds_its_traceback_at_debug_level() -> None:
    failed = _failed("ValueError('the value 4111 1111')", debug=True)
    assert failed.returncode == 1
    assert "DEBUG The command failed.\nTraceback" in failed.stderr
    assert "ValueError: the value 4111 1111" in failed.stderr
