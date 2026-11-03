"""The command line of the tool: `data-profiler [--debug] STAGE ENVIRONMENT [--project DIR]`.

It runs a stage on one environment of a project, the project in the current directory if none is
given: `scan` the tables of its database into its profile and workspace, the overrides of the
project taken as given, `describe` the names of its profile, by the concepts of the profile and of
the overrides and by the language model of the project, into its profile - with `--anew`, dropping
first what the language model filled -, and `report` its profile, the overrides laid over it, into
its report, the last two without the database. The project completes the variables of the process by
its `.env`, so that certificates and proxies set there reach the connection to the database.
`data_profiler.commands.run` configures the log and ends the program when the stage fails.
"""

import logging
import os
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path
from typing import Final

from data_profiler.commands import run
from data_profiler.describe import describe, forgotten
from data_profiler.llm import LanguageModelError, Ollama
from data_profiler.overrides import Overrides, OverridesError
from data_profiler.profile import Profile, ProfileError
from data_profiler.project import Environment, Project, ProjectError
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
    LanguageModelError,
    ReportError,
)


def main() -> None:
    """Runs the command given on the command line."""
    parser = ArgumentParser(
        prog="data-profiler", description="Profiles the tables of an SQL database."
    )
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    commands = parser.add_subparsers(dest="command", required=True)
    stages: dict[str, tuple[_Stage, str]] = {
        "scan": (_scan, "scan the tables of an environment of a project"),
        "describe": (_describe, "describe the names of the profile of an environment"),
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
    commands.choices["describe"].add_argument(
        "--anew",
        dest="stage",
        action="store_const",
        const=_describe_anew,
        help="drop first what the language model filled, to describe the profile anew",
    )
    arguments = parser.parse_args()
    run(
        lambda: _run(arguments.stage, arguments.project, arguments.environment),
        arguments.debug,
        _SHOWN,
    )


type _Stage = Callable[[Project, Environment], None]
"""A stage, run on an environment of a project."""


def _run(stage: _Stage, directory: Path, name: str) -> None:
    """Runs `stage` on the environment `name` of the project in `directory`."""
    project = Project.read(directory, os.environ)
    stage(project, project.environment(name))


def _scan(project: Project, environment: Environment) -> None:
    """Scans `environment` of `project` into its results."""
    overrides = Overrides.read(project.overrides)
    with connect(environment.url, environment.user, environment.password) as source:
        workspace = Workspace.open(environment.workspace, source.catalog, source.schema)
        scan(source, project.tables, workspace, project.types, overrides, environment.profile)
    _logger.info("Wrote the profile of %s to %s", environment.name, environment.profile)


def _describe(project: Project, environment: Environment) -> None:
    """Describes the profile of `environment` of `project`."""
    _described(project, environment, Profile.read(environment.profile))


def _describe_anew(project: Project, environment: Environment) -> None:
    """Describes the profile of `environment` of `project` anew, as if it was not described."""
    _described(project, environment, forgotten(Profile.read(environment.profile)))


def _described(project: Project, environment: Environment, profile: Profile) -> None:
    """Describes `profile`, of `environment` of `project`, into its directory."""
    overrides = Overrides.read(project.overrides)
    llm = Ollama(project.ollama, project.llm)
    workspace = Workspace.open(environment.workspace, profile.catalog, profile.schema)
    describe(profile, overrides, llm, workspace, environment.profile)
    _logger.info("Wrote the profile of %s to %s", environment.name, environment.profile)


def _report(project: Project, environment: Environment) -> None:
    """Renders the profile of `environment` of `project` as its report."""
    overrides = Overrides.read(project.overrides)
    write_report(Profile.read(environment.profile), overrides, environment.report)
    _logger.info("Wrote the report of %s to %s", environment.name, environment.report)
