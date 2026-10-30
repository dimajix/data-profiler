"""Commands: the frame every command line of the project runs its work in.

A command runs its work through `run`, which configures the log, to standard error - at debug
level with `--debug` -, and ends the program with the exit code 1 when the work fails: of an error
whose message may be shown, the message; of any other, that it failed unexpectedly. The traceback
goes to the log at debug level.
"""

import logging
import sys
from collections.abc import Callable
from typing import Final

_logger = logging.getLogger(__name__)

_FORMAT: Final = "%(levelname)s %(message)s"


def run(work: Callable[[], None], debug: bool, shown: tuple[type[Exception], ...]) -> None:
    """Runs `work` with the log configured, ending the program with code 1 when it fails.

    Args:
        work: What the command does.
        debug: Whether the log is written at debug level, rather than at info level.
        shown: The classes of the errors whose message may be shown to users.

    Raises:
        SystemExit: With the code 1, when `work` fails.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format=_FORMAT)  # noqa: TID251  # the frame of every command
    try:
        work()
    except shown as error:
        _logger.error("%s", error)
        _logger.debug("The command failed.", exc_info=True)
        sys.exit(1)  # noqa: TID251  # the frame of every command
    except Exception:
        _logger.error("The command failed unexpectedly; with --debug, the log says why.")
        _logger.debug("The command failed.", exc_info=True)
        sys.exit(1)  # noqa: TID251  # the frame of every command
