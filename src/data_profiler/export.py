"""The templates of the stage export: the forms the profile is exported in, overrides laid over.

A `Template` is one form of the profile, written into a directory of the environment of its own,
named after it: the report, `html`, first. The stage reads the profile and the overrides alone,
never the database or the workspace, so that it holds what the profile may hold. Which templates
there are, the command line says; a template is chosen by its name.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final

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

    @abstractmethod
    def write(self, profile: Profile, overrides: Overrides, directory: Path) -> None:
        """Writes `profile`, `overrides` laid over it, into `directory`.

        Each file it writes is written whole or not at all.

        Args:
            profile: The profile, as it was read.
            overrides: The overrides of the project.
            directory: The directory of the template, made where it does not exist.

        Raises:
            OverridesError: The overrides name what the profile does not have, as
                `Overrides.laid_over` says.
            ExportError: The directory or a file cannot be written.
        """
