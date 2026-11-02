"""Projects: a database profiled in environments, its configuration and results in one place.

A project is a directory. Its configuration, `project.yml`, is a document that names the tables to
profile, for the whole project, the semantic types of its own its columns are checked for beside
those of the tool, and the environments the database is profiled in - dev, test, prod -, each by
the URL of its schema, and the user and the password it is reached as; beside it, `overrides.yml`
gives by hand what the profiles of all environments take as given. Each environment keeps its
results in a directory of its own, named after it: its profile, its workspace and its report.

A value of the configuration that is `${NAME}` is taken from the variable `NAME`; the password is
given only so, never written out, so that the configuration can be committed and shared. The
variables are those of the process, completed by the `.env` of the project, which is not
committed and does not override what the process sets. They are resolved when the URL, the user or
the password of an environment is asked for, so that an environment can be used without those of
the others being set, and its results without its own.
"""

import re
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from re import Pattern, PatternError
from typing import Final, Self

from dotenv import dotenv_values
from pydantic import TypeAdapter

from data_profiler.detect import SemanticType
from data_profiler.documents import DocumentError, read_document
from data_profiler.profile import SemanticTypes

FORMAT: Final = 3
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
class _Settings:
    """How an environment is reached, as the configuration gives it: values or `${NAME}`."""

    url: str
    user: str
    password: str


class Environment:
    """An environment of a project: the schema it profiles, and the directory of its results.

    Its URL, user and password are resolved when they are asked for, so that a stage that does not
    reach the database, such as `report`, needs none of them.

    Attributes:
        name: The name of the environment, such as `dev` or `prod`.
        directory: The directory of its results, in the directory of the project.
    """

    def __init__(
        self, name: str, file: Path, settings: _Settings, variables: Mapping[str, str]
    ) -> None:
        """Takes what the project `file` gives of the environment, and the variables of it."""
        self.name = name
        self.directory = file.parent / name
        self._file = file
        self._settings = settings
        self._variables = variables

    @property
    def url(self) -> str:
        """The schema the environment profiles, as `source.connect` takes it.

        Raises:
            ProjectError: The URL is a variable that is not set.
        """
        return self._resolved("url", self._settings.url)

    @property
    def user(self) -> str:
        """The user the environment is reached as.

        Raises:
            ProjectError: The user is a variable that is not set.
        """
        return self._resolved("user", self._settings.user)

    @property
    def password(self) -> str:
        """The password of the user; never shown.

        Raises:
            ProjectError: The password is a variable that is not set.
        """
        return self._resolved("password", self._settings.password)

    @property
    def profile(self) -> Path:
        """The file of the profile of the environment."""
        return self.directory / "profile.yml"

    @property
    def workspace(self) -> Path:
        """The directory of the workspace of the environment."""
        return self.directory / "workspace"

    @property
    def report(self) -> Path:
        """The file of the report of the environment."""
        return self.directory / "report.html"

    def _resolved(self, setting: str, value: str) -> str:
        """`value` of `setting`, or the variable it names."""
        variable = _VARIABLE.fullmatch(value)
        if variable is None:
            return value
        found = self._variables.get(variable[1])
        if found is None:
            raise ProjectError(
                f"{self._file}: the {setting} of the environment {self.name} is the variable"
                f" {variable[1]}, which neither the process sets nor"
                f" {self._file.parent / _VARIABLES}"
            )
        return found


@dataclass(frozen=True)
class _Configuration:
    """The configuration of a project, as its file holds it."""

    tables: str | tuple[str, ...]
    environments: Mapping[str, _Settings]
    # Checked by its validator, not after it as the others are, as the profile holds the types too
    # and checks them the same way.
    types: SemanticTypes = ()


_ADAPTER: Final = TypeAdapter(_Configuration)


class Project:
    """A database profiled in environments: the tables to profile, and each environment.

    Attributes:
        tables: The names of the tables to profile, matched whole.
        types: The semantic types of the project, beside those of the tool.
    """

    def __init__(
        self,
        file: Path,
        tables: Pattern[str],
        types: tuple[SemanticType, ...],
        environments: Mapping[str, _Settings],
        variables: Mapping[str, str],
    ) -> None:
        """Takes what `read` has read of `file`, and the variables to resolve its values by."""
        self.tables = tables
        self.types = types
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
                no document of the format, names an environment other than in lower case letters,
                digits, `-` and `_`, beginning with a letter or a digit, gives a password other
                than by a variable, a URL or a user with a variable in it rather than as a whole,
                its tables by no regular expression, or a semantic type of its own that cannot be
                made, as `detect.project_type` says.
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
            for setting, value in (("url", settings.url), ("user", settings.user)):
                if "${" in value and not _VARIABLE.fullmatch(value):
                    raise ProjectError(
                        f"{file}: the environment {name} gives its {setting} with a variable in"
                        " it, but a variable is taken only as the whole value"
                    )
        tables = configuration.tables
        try:
            pattern = re.compile(
                tables if isinstance(tables, str) else "|".join(map(re.escape, tables))
            )
        except PatternError as error:
            raise ProjectError(f"{file}: tables is no regular expression: {error}") from error
        _complete(variables, directory / _VARIABLES)
        return cls(file, pattern, configuration.types, configuration.environments, variables)

    @property
    def overrides(self) -> Path:
        """The file of the overrides of the project, the same for all its environments."""
        return self._file.parent / "overrides.yml"

    def environment(self, name: str) -> Environment:
        """The environment `name`, its values taken from the variables when they are asked for.

        Args:
            name: The name of the environment.

        Returns:
            The environment.

        Raises:
            ProjectError: The project has no environment `name`.
        """
        settings = self._environments.get(name)
        if settings is None:
            known = ", ".join(sorted(self._environments)) or "none"
            raise ProjectError(f"{self._file} has no environment {name}; it has: {known}")
        return Environment(name, self._file, settings, self._variables)


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
