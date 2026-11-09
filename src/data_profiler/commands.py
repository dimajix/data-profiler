"""Commands: the frame every command line of the project runs its work in.

A command runs its work through `run`, which configures the log, to standard error - at debug
level with `--debug` -, and ends the program with the exit code 1 when the work fails: of an error
whose message may be shown, the message; of any other, that it failed unexpectedly. Work interrupted
by Ctrl-C is no failure: the log says so, and the program ends by the signal, which a shell reports
as the exit code 130. The traceback goes to the log at debug level in either case.
"""

import logging
import signal
import sys
from collections.abc import Callable
from typing import Final

_logger = logging.getLogger(__name__)

_FORMAT: Final = "%(levelname)s %(message)s"


def run(work: Callable[[], None], debug: bool, shown: tuple[type[Exception], ...]) -> None:
    """Runs `work` with the log configured, ending the program when it fails or is interrupted.

    Args:
        work: What the command does.
        debug: Whether the log is written at debug level, rather than at info level.
        shown: The classes of the errors whose message may be shown to users.

    Raises:
        SystemExit: With the code 1, when `work` fails. Work interrupted raises nothing: the program
            ends by the signal.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format=_FORMAT)  # noqa: TID251  # the frame of every command
    try:
        work()
    except shown as error:
        _logger.error("%s", error)
        _logger.debug("The command failed.", exc_info=True)
        sys.exit(1)  # noqa: TID251  # the frame of every command
    except KeyboardInterrupt:
        _logger.info("The command was interrupted.")
        _logger.debug("Where the command was interrupted:", exc_info=True)
        # By the signal rather than an exit code, as Python itself ends on Ctrl-C: a shell goes on
        # with the next command of a script after a program that exits, whatever the code.
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.raise_signal(signal.SIGINT)  # noqa: TID251  # the frame of every command
    except Exception:
        _logger.error("The command failed unexpectedly; with --debug, the log says why.")
        _logger.debug("The command failed.", exc_info=True)
        sys.exit(1)  # noqa: TID251  # the frame of every command
