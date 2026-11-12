"""The templates of the stage export: the forms the profile is exported in, overrides laid over.

A `Template` is one form of the profile, written into a directory of the environment of its own,
named after it: the report, `html`, first. A template gives its files alone, of the profile with
the overrides laid over it; `Template.write` does for each what all share - it warns of what the
overrides give that the profile does not take, lays them over it, makes the directory and writes
each file whole or not at all. The stage reads the profile and the overrides alone, never the
database or the workspace, so that it holds what the profile may hold. Which templates there are,
the command line says; a template is chosen by its name.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from data_profiler.files import write_whole
from data_profiler.overrides import Overrides
from data_profiler.profile import Profile


class ExportError(Exception):
    """An export that cannot be written: its directory or file, and what is wrong."""


class Template(ABC):
    """A form the profile is exported in, the overrides laid over it, into a directory of its own.

    Attributes:
        name: The name of the template, as `--template` gives it; it names its directory.
    """

    def __init__(self, name: str) -> None:
        """Takes the name of the template."""
        self.name: Final = name

    def write(self, profile: Profile, overrides: Overrides, directory: Path) -> None:
        """Writes the files of `profile`, `overrides` laid over it, into `directory`.

        It warns of what the overrides give that the profile does not take, lays them over it, and
        writes each file whole or not at all.

        Args:
            profile: The profile, as it was read.
            overrides: The overrides of the project.
            directory: The directory of the template, made where it does not exist.

        Raises:
            OverridesError: The overrides name what the profile does not have, as
                `Overrides.laid_over` says.
            ExportError: The directory or a file cannot be written.
        """
        overrides.warn_unused(profile)
        files = self.files(overrides.laid_over(profile), overrides)
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ExportError(f"{directory} cannot be written: {error.strerror}") from error
        for name, content in files.items():
            path = directory / name
            try:
                write_whole(path, content)
            except OSError as error:
                raise ExportError(f"{path} cannot be written: {error.strerror}") from error

    @abstractmethod
    def files(self, profile: Profile, overrides: Overrides) -> Mapping[str, bytes]:
        """The files of the template, by their names in its directory, each with its content.

        Args:
            profile: The profile, the overrides laid over it already.
            overrides: The overrides of the project, for what the template shows of them beyond
                the profile, such as the concepts given.

        Returns:
            The content of each file, by its name, of no directory.
        """
