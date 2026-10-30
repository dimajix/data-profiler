"""The command line of the tool: `data-profiler [--debug] scan ENVIRONMENT [--project DIR]`.

It runs a stage on one environment of a project, the project in the current directory if none is
given. The project completes the variables of the process by its `.env`, so that certificates and
proxies set there reach the connection to the database. `data_profiler.commands.run` configures the
log and ends the program when the stage fails.
"""

import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Final

from data_profiler.commands import run
from data_profiler.profile import ProfileError
from data_profiler.project import Project, ProjectError
from data_profiler.scan import scan
from data_profiler.source import SourceError, connect
from data_profiler.workspace import Workspace, WorkspaceError

_logger = logging.getLogger(__name__)

# The errors whose message may be shown.
_SHOWN: Final = (ProjectError, SourceError, WorkspaceError, ProfileError)


def main() -> None:
    """Runs the command given on the command line."""
    parser = ArgumentParser(
        prog="data-profiler", description="Profiles the tables of an SQL database."
    )
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("scan", help="scan the tables of an environment of a project")
    command.add_argument("environment", help="the name of the environment")
    command.add_argument(
        "--project",
        type=Path,
        default=Path(),
        help="the directory of the project (default: the current one)",
    )
    arguments = parser.parse_args()
    run(lambda: _scan(arguments.project, arguments.environment), arguments.debug, _SHOWN)


def _scan(directory: Path, name: str) -> None:
    """Scans the environment `name` of the project in `directory` into its results."""
    project = Project.read(directory, os.environ)
    environment = project.environment(name)
    with connect(environment.url, environment.password) as source:
        workspace = Workspace.open(environment.workspace, source.catalog, source.schema)
        profile = scan(source, project.tables, workspace)
    profile.write(environment.profile)
    _logger.info("Wrote the profile of %s to %s", name, environment.profile)
