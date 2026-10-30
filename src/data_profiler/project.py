"""Projects: a database profiled in environments, its configuration and results in one place.

A project is a directory. Its configuration, `project.yml`, is a document that names the tables to
profile, for the whole project, and the environments the database is profiled in - dev, test, prod
-, each by the URL of its schema and its password; beside it, `overrides.yml` gives by hand what
the profiles of all environments take as given. Each environment keeps its results in a directory
of its own, named after it: its profile and its workspace.

A value of the configuration that is `${NAME}` is taken from the variable `NAME`; the password is
given only so, never written out, so that the configuration can be committed and shared. The
variables are those of the process, completed by the `.env` of the project, which is not
committed and does not override what the process sets. They are resolved when an environment is,
so that an environment can be used without those of the others being set.
"""

import re
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern, PatternError
from typing import Final, Self

from dotenv import dotenv_values
from pydantic import TypeAdapter

from data_profiler.documents import DocumentError, read_document

FORMAT: Final = 1
"""The version of the format of the configuration of a project, raised as `profile.FORMAT` is."""

# The name of an environment, which is the name of its directory, the same on every system, and an
# argument of the command line, never taken for an option there.
_NAME: Final = re.compile(r"[a-z0-9][a-z0-9_-]*")
# The file of the variables of a project, which completes those of the process.
_VARIABLES: Final = ".env"
# A value taken from a variable, by its name.
_VARIABLE: Final = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ProjectError(Exception):
    """A project that cannot be read, or an environment of it that cannot be resolved."""


@dataclass(frozen=True)
class Environment:
    """An environment of a project: the schema it profiles, and the directory of its results.

    Attributes:
        name: The name of the environment, such as `dev` or `prod`.
        url: The schema the environment profiles, as `source.connect` takes it.
        directory: The directory of its results, in the directory of the project.
        password: The password of the user the URL names; never shown.
    """

    name: str
    url: str
    directory: Path
    password: str = field(repr=False)

    @property
    def profile(self) -> Path:
        """The file of the profile of the environment."""
        return self.directory / "profile.yml"

    @property
    def workspace(self) -> Path:
        """The directory of the workspace of the environment."""
        return self.directory / "workspace"


@dataclass(frozen=True)
class _Settings:
    """How an environment is reached, as the configuration gives it: values or `${NAME}`."""

    url: str
    password: str


@dataclass(frozen=True)
class _Configuration:
    """The configuration of a project, as its file holds it."""

    tables: str | tuple[str, ...]
    environments: Mapping[str, _Settings]


_ADAPTER: Final = TypeAdapter(_Configuration)


class Project:
    """A database profiled in environments: the tables to profile, and each environment.

    Attributes:
        tables: The names of the tables to profile, matched whole.
    """

    def __init__(
        self,
        file: Path,
        tables: Pattern[str],
        environments: Mapping[str, _Settings],
        variables: Mapping[str, str],
    ) -> None:
        """Takes what `read` has read of `file`, and the variables to resolve its values by."""
        self.tables = tables
        self._file = file
        self._environments = environments
        self._variables = variables

    @classmethod
    def read(cls, directory: Path, variables: MutableMapping[str, str]) -> Self:
        """The project in `directory`, as its configuration `project.yml` describes it.

        Args:
            directory: The directory of the project.
            variables: The variables of the process, which the `.env` of the project completes,
                where there is one, and which the values `${NAME}` are taken from when an
                environment is resolved.

        Returns:
            The project.

        Raises:
            ProjectError: The configuration or the `.env` cannot be read, the configuration is
                no document of the format, names
                an environment other than in lower case letters, digits, `-` and `_`, beginning
                with a letter or a digit, gives a password other than by a variable, a URL with a
                variable in it rather than as a whole, or its tables by no regular expression.
        """
        file = directory / "project.yml"
        try:
            configuration = read_document(file, _ADAPTER, FORMAT)
        except DocumentError as error:
            raise ProjectError(str(error)) from error
        for name, settings in configuration.environments.items():
            if not _NAME.fullmatch(name):
                raise ProjectError(
                    f"{file}: the environment {name!r} is named other than in lower case letters,"
                    " digits, '-' and '_', beginning with a letter or a digit"
                )
            if not _VARIABLE.fullmatch(settings.password):
                raise ProjectError(
                    f"{file}: the environment {name} gives its password other than as ${{NAME}},"
                    " a variable"
                )
            if "${" in settings.url and not _VARIABLE.fullmatch(settings.url):
                raise ProjectError(
                    f"{file}: the environment {name} gives its url with a variable in it, but a"
                    " variable is taken only as the whole value"
                )
        tables = configuration.tables
        try:
            pattern = re.compile(
                tables if isinstance(tables, str) else "|".join(map(re.escape, tables))
            )
        except PatternError as error:
            raise ProjectError(f"{file}: tables is no regular expression: {error}") from error
        _complete(variables, directory / _VARIABLES)
        return cls(file, pattern, configuration.environments, variables)

    @property
    def overrides(self) -> Path:
        """The file of the overrides of the project, the same for all its environments."""
        return self._file.parent / "overrides.yml"

    def environment(self, name: str) -> Environment:
        """The environment `name`, its values taken from the variables where they name one.

        Args:
            name: The name of the environment.

        Returns:
            The environment.

        Raises:
            ProjectError: The project has no environment `name`, or a variable it names is not
                set.
        """
        settings = self._environments.get(name)
        if settings is None:
            known = ", ".join(sorted(self._environments)) or "none"
            raise ProjectError(f"{self._file} has no environment {name}; it has: {known}")
        return Environment(
            name=name,
            url=self._resolved(name, "url", settings.url),
            directory=self._file.parent / name,
            password=self._resolved(name, "password", settings.password),
        )

    def _resolved(self, name: str, setting: str, value: str) -> str:
        """`value` of the setting of the environment `name`, or the variable it names."""
        variable = _VARIABLE.fullmatch(value)
        if variable is None:
            return value
        found = self._variables.get(variable[1])
        if found is None:
            raise ProjectError(
                f"{self._file}: the {setting} of the environment {name} is the variable"
                f" {variable[1]}, which neither the process sets nor"
                f" {self._file.parent / _VARIABLES}"
            )
        return found


def _complete(variables: MutableMapping[str, str], path: Path) -> None:
    """Completes `variables` by those of the file `path`, where there is one, overriding none."""
    try:
        found = dotenv_values(path)
    except OSError as error:
        raise ProjectError(f"{path} cannot be read: {error.strerror}") from error
    except UnicodeDecodeError as error:
        # Its message holds the bytes it failed on, which may be of a password.
        raise ProjectError(f"{path} is no text in UTF-8") from error
    for name, value in found.items():
        if value is not None:
            variables.setdefault(name, value)
