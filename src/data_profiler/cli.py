"""The command line of the tool: `data-profiler [--debug] STAGE ENVIRONMENT [--project DIR]`.

It runs a stage on one environment of a project, the project in the current directory if none is
given: `scan` the tables of its database into its profile and workspace, the overrides of the
project taken as given, `relate` the tables of its profile to the keys of each other, by its
database, the overrides taken as given, `describe` the names of its profile, by the concepts of the
profile and of the overrides and by the language model of the project, into its profile - with
`--anew`, dropping first what the language model filled, with `--without-llm`, asking none -,
`adopt` the concepts its profile proposes into the overrides, asking a person at the terminal about
each, and `export` its profile, the overrides laid over it, in a template - `--template`, the
report, `html`, where none is given -, the last three without the database. The project completes
the variables of the process by its `.env`, so that certificates and proxies set there reach the
connection to the database. `data_profiler.commands.run` configures the log and ends the program
when the stage fails.
"""

import logging
import os
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Final

from data_profiler.adopt import AdoptError, adopt
from data_profiler.commands import run
from data_profiler.describe import describe, forgotten
from data_profiler.export import ExportError, Template
from data_profiler.llm import LanguageModelError, Ollama
from data_profiler.overrides import Overrides, OverridesError
from data_profiler.profile import Profile, ProfileError
from data_profiler.project import Environment, Project, ProjectError
from data_profiler.relate import relate
from data_profiler.report import Report
from data_profiler.scan import scan
from data_profiler.source import SourceError, connect
from data_profiler.workspace import Workspace, WorkspaceError

_logger = logging.getLogger(__name__)

# The template the profile is exported in where none is given: the report. The templates are made
# once, here, unlike the language model, which a stage makes as the project names it: argparse
# needs their names before it reads the arguments, for the choices and the default of --template.
_REPORT: Final = Report()

# The templates the profile is exported in, by their names.
_TEMPLATES: Final[dict[str, Template]] = {template.name: template for template in (_REPORT,)}

# The errors whose message may be shown.
_SHOWN: Final = (
    ProjectError,
    SourceError,
    WorkspaceError,
    ProfileError,
    OverridesError,
    LanguageModelError,
    ExportError,
    AdoptError,
)


def main() -> None:
    """Runs the command given on the command line."""
    parser = ArgumentParser(
        prog="data-profiler", description="Profiles the tables of an SQL database."
    )
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    commands = parser.add_subparsers(dest="command", required=True)
    stages: dict[str, tuple[_Command, str]] = {
        "scan": (lambda _: _scan, "scan the tables of an environment of a project"),
        "relate": (lambda _: _relate, "relate the tables of the profile of an environment"),
        "describe": (_describing, "describe the names of the profile of an environment"),
        "adopt": (
            lambda _: _adopt,
            "take the concepts proposed into the overrides, asking of each",
        ),
        "export": (_exporting, "export the profile of an environment of a project in a template"),
    }
    for name, (made, summary) in stages.items():
        command = commands.add_parser(name, help=summary)
        command.add_argument("environment", help="the name of the environment")
        command.add_argument(
            "--project",
            type=Path,
            default=Path(),
            help="the directory of the project (default: the current one)",
        )
        command.set_defaults(made=made)
    commands.choices["describe"].add_argument(
        "--anew",
        action="store_true",
        help="drop first what the language model filled, to describe the profile anew",
    )
    commands.choices["describe"].add_argument(
        "--without-llm",
        action="store_true",
        help="ask no language model: split and read the names by the concepts alone",
    )
    commands.choices["export"].add_argument(
        "--template",
        choices=_TEMPLATES,
        default=_REPORT.name,
        help=f"the template to export the profile in (default: {_REPORT.name})",
    )
    arguments = parser.parse_args()
    stage: _Stage = arguments.made(arguments)
    run(lambda: _run(stage, arguments.project, arguments.environment), arguments.debug, _SHOWN)


type _Stage = Callable[[Project, Environment], None]
"""A stage, run on an environment of a project."""

type _Command = Callable[[Namespace], _Stage]
"""The stage of a command, made of the options given of it, so that argparse stays in `main`."""


def _run(stage: _Stage, directory: Path, name: str) -> None:
    """Runs `stage` on the environment `name` of the project in `directory`."""
    project = Project.read(directory, os.environ)
    stage(project, project.environment(name))


def _scan(project: Project, environment: Environment) -> None:
    """Scans `environment` of `project` into its results."""
    overrides = Overrides.read(project.overrides)
    with connect(environment.url, environment.user, environment.password) as source:
        workspace = Workspace.open(environment.workspace, source.catalog, source.schema)
        scan(
            source,
            project.tables,
            workspace,
            project.types,
            project.list_separator,
            overrides,
            environment.profile,
        )
    _logger.info("Wrote the profile of %s to %s", environment.name, environment.profile)


def _relate(project: Project, environment: Environment) -> None:
    """Relates the tables of the profile of `environment` of `project` to each other."""
    overrides = Overrides.read(project.overrides)
    with connect(environment.url, environment.user, environment.password) as source:
        relate(source, overrides, environment.profile)
    _logger.info("Wrote the profile of %s to %s", environment.name, environment.profile)


def _describing(options: Namespace) -> _Stage:
    """The stage describe, with its options `--anew` and `--without-llm`."""
    return partial(_describe, anew=options.anew, without_llm=options.without_llm)


def _describe(project: Project, environment: Environment, *, anew: bool, without_llm: bool) -> None:
    """Describes the profile of `environment` of `project`.

    Its two options are independent of each other, each of the four of them together a stage, so
    that they are flags of one function rather than a function each.

    Args:
        project: The project.
        environment: The environment, whose profile is described.
        anew: Whether what the language model filled is dropped first, as if it was not described.
        without_llm: Whether no language model is asked, so that the project needs none.
    """
    profile = Profile.read(environment.profile)
    if anew:
        profile = forgotten(profile)
    overrides = Overrides.read(project.overrides)
    llm = None if without_llm else Ollama(project.ollama, project.llm)
    workspace = Workspace.open(environment.workspace, profile.catalog, profile.schema)
    describe(profile, overrides, llm, workspace, environment.profile)
    _logger.info("Wrote the profile of %s to %s", environment.name, environment.profile)


def _adopt(project: Project, environment: Environment) -> None:
    """Asks about the concepts the profile of `environment` proposes, into the overrides."""
    if not sys.stdin.isatty():
        raise AdoptError("adopt asks a person, and its input is no terminal")
    adopt(Profile.read(environment.profile).glossary, project, input)
    _logger.info("Went through the concepts of the profile of %s", environment.name)


def _exporting(options: Namespace) -> _Stage:
    """The stage export, with its option `--template`."""
    return partial(_export, template=_TEMPLATES[options.template])


def _export(project: Project, environment: Environment, *, template: Template) -> None:
    """Exports the profile of `environment` of `project` in `template`."""
    overrides = Overrides.read(project.overrides)
    directory = environment.export(template.name)
    template.write(Profile.read(environment.profile), overrides, directory)
    _logger.info(
        "Exported the profile of %s in %s to %s", environment.name, template.name, directory
    )
