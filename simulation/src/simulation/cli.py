"""The command line of the simulation: `simulation [--debug] load PROFILE [--seed N]`.

It loads the tables of a profile into the simulation environment, which has to run, and logs what
Trino counts of them afterwards; `data_profiler.commands.run` configures the log and ends the
program when the load fails.
"""

import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Final

from data_profiler.commands import run
from data_profiler.profile import Profile, ProfileError
from simulation import SimulationError
from simulation.environment import Simulation

_logger = logging.getLogger(__name__)

# The errors whose message may be shown.
_SHOWN: Final = (ProfileError, SimulationError)


def main() -> None:
    """Runs the command given on the command line."""
    parser = ArgumentParser(prog="simulation", description="The simulation environment.")
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="load the tables of a profile, with generated data")
    load.add_argument("profile", type=Path, help="the file of the profile")
    load.add_argument("--seed", type=int, default=0, help="the seed of the values (default: 0)")
    arguments = parser.parse_args()
    run(lambda: _load(arguments.profile, arguments.seed), arguments.debug, _SHOWN)


def _load(path: Path, seed: int) -> None:
    """Loads the profile in `path` into the simulation environment, its values made by `seed`."""
    profile = Profile.read(path)
    with Simulation.connect() as simulation:
        simulation.load(profile, seed)
        for table in profile.tables:
            rows = simulation.count(profile.schema, table.name)
            _logger.info("Trino counts %s.%s: %d rows", profile.schema, table.name, rows)
