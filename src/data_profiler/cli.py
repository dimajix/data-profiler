"""The command line of the tool: `data-profiler [--debug] STAGE ENVIRONMENT [--project DIR]`.

It runs a stage on one environment of a project, the project in the current directory if none is
given: `scan` the tables of its database into its profile and workspace, `report` its profile, the
overrides of the project laid over it, into its report, without the database. The project
completes the variables of the process by its `.env`, so that certificates and proxies set there
reach the connection to the database. `data_profiler.commands.run` configures the log and ends the
program when the stage fails.
"""

import logging
import os
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path
from typing import Final

from data_profiler.commands import run
from data_profiler.overrides import Overrides, OverridesError
from data_profiler.profile import Profile, ProfileError
from data_profiler.project import Project, ProjectError
from data_profiler.report import ReportError, write_report
from data_profiler.scan import scan
from data_profiler.source import SourceError, connect
from data_profiler.workspace import Workspace, WorkspaceError

_logger = logging.getLogger(__name__)

# The errors whose message may be shown.
_SHOWN: Final = (
    ProjectError,
    SourceError,
    WorkspaceError,
    ProfileError,
    OverridesError,
    ReportError,
)


def main() -> None:
    """Runs the command given on the command line."""
    parser = ArgumentParser(
        prog="data-profiler", description="Profiles the tables of an SQL database."
    )
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    commands = parser.add_subparsers(dest="command", required=True)
    stages: dict[str, tuple[Callable[[Path, str], None], str]] = {
        "scan": (_scan, "scan the tables of an environment of a project"),
        "report": (_report, "render the profile of an environment of a project as HTML"),
    }
    for name, (stage, summary) in stages.items():
        command = commands.add_parser(name, help=summary)
        command.add_argument("environment", help="the name of the environment")
        command.add_argument(
            "--project",
            type=Path,
            default=Path(),
            help="the directory of the project (default: the current one)",
        )
        command.set_defaults(stage=stage)
    arguments = parser.parse_args()
    run(lambda: arguments.stage(arguments.project, arguments.environment), arguments.debug, _SHOWN)


def _scan(directory: Path, name: str) -> None:
    """Scans the environment `name` of the project in `directory` into its results."""
    project = Project.read(directory, os.environ)
    environment = project.environment(name)
    with connect(environment.url, environment.password) as source:
        workspace = Workspace.open(environment.workspace, source.catalog, source.schema)
        profile = scan(source, project.tables, workspace)
    profile.write(environment.profile)
    _logger.info("Wrote the profile of %s to %s", name, environment.profile)


def _report(directory: Path, name: str) -> None:
    """Renders the profile of the environment `name` of the project in `directory` as its report."""
    project = Project.read(directory, os.environ)
    environment = project.environment(name)
    profile = Overrides.read(project.overrides).laid_over(Profile.read(environment.profile))
    write_report(profile, environment.report)
    _logger.info("Wrote the report of %s to %s", name, environment.report)
