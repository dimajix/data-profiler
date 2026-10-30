"""The stage report: a profile rendered as one HTML document, which a browser shows on its own.

The document holds its styles inside, and no script, so that it can be sent and printed as it is.
It shows each table with its columns - their original and harmonized names, types, statistics,
semantic types, sensitivity and the values of their enumerations - and the glossary, each term with
its word and where it appears. It renders what the profile holds, and nothing of the workspace:
the values in it are those the profile may hold, which the template escapes.
"""

from pathlib import Path
from typing import Final

from jinja2 import Environment, PackageLoader, StrictUndefined

from data_profiler.files import write_whole
from data_profiler.glossary import harmonized, occurrences
from data_profiler.profile import Profile

# The places a term of the glossary is shown with, before the number of the others.
_PLACES: Final = 8

_TEMPLATES: Final = Environment(
    loader=PackageLoader("data_profiler", "templates"),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class ReportError(Exception):
    """A report that cannot be written: its file, and what is wrong."""


def render(profile: Profile) -> str:
    """The report of `profile`, one HTML document with its styles inside."""
    glossary = profile.glossary
    columns = [column for table in profile.tables for column in table.columns]
    return _TEMPLATES.get_template("report.html").render(
        profile=profile,
        column_count=len(columns),
        sensitive_count=sum(1 for column in columns if column.sensitive),
        end=lambda value: "withheld" if value is None else value,
        terms=occurrences(profile),
        places=_PLACES,
        harmonized=lambda name: harmonized(name, glossary),
    )


def write_report(profile: Profile, path: Path) -> None:
    """Writes the report of `profile` to `path`, whole or not at all.

    Args:
        profile: The profile, the overrides laid over it.
        path: The file of the report.

    Raises:
        ReportError: The file cannot be written.
    """
    try:
        write_whole(path, render(profile).encode("utf-8"))
    except OSError as error:
        raise ReportError(f"{path} cannot be written: {error.strerror}") from error
