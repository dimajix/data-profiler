"""The stage report: a profile rendered as one HTML document, which a browser shows on its own.

The document holds its styles inside, and no script, so that it can be sent and printed as it is.
It shows the profile with the overrides of the project laid over it: what the database holds, where
it is given; each table, with what it holds, where it is given, and with its columns -
their original names and harmonized names, composed from their readings or given, descriptions,
types, statistics, the shares of their nulls and sentinels among them, semantic types, sensitivity,
the values of their enumerations and each of their sentinels -, with the groups of its columns
filled together and the harmonized names two of its columns share; and the glossary, each concept
with its abbreviations and description, those proposed told apart from those given, and each term
of no concept, as describe split the names, with where it appears. It renders what the profile
holds, and nothing of the workspace: the values in it are those the profile may hold, which the
template escapes.
"""

from pathlib import Path
from typing import Final

from jinja2 import Environment, PackageLoader, StrictUndefined

from data_profiler.files import write_whole
from data_profiler.glossary import Glossary, unknown
from data_profiler.overrides import Overrides
from data_profiler.profile import Profile

# The places a term of no concept is shown with, before the number of the others.
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


def render(profile: Profile, overrides: Overrides) -> str:
    """The report of `profile`, with `overrides` laid over it: one HTML document, its styles inside.

    Args:
        profile: The profile, as it was read.
        overrides: The overrides of the project.

    Returns:
        The document.

    Raises:
        OverridesError: The overrides name what the profile does not have, as
            `Overrides.laid_over` says.
    """
    overrides.warn_unused(profile)
    profile = overrides.laid_over(profile)
    glossary = Glossary(profile.glossary)
    columns = [column for table in profile.tables for column in table.columns]
    return _TEMPLATES.get_template("report.html").render(
        profile=profile,
        column_count=len(columns),
        sensitive_count=sum(1 for column in columns if column.sensitive),
        end=lambda value: "withheld" if value is None else value,
        # A share of no rows is none, written as a dash, as the template writes what is not known.
        share=lambda count, rows: f"{count / rows:.0%}" if rows else "\u2013",
        unknown=unknown(profile),
        given=overrides.glossary.keys(),
        places=_PLACES,
        harmonized=glossary.harmonized,
        collisions=glossary.collisions,
    )


def write_report(profile: Profile, overrides: Overrides, path: Path) -> None:
    """Writes the report of `profile`, `overrides` laid over it, to `path`, whole or not at all.

    Args:
        profile: The profile, as it was read.
        overrides: The overrides of the project.
        path: The file of the report.

    Raises:
        OverridesError: The overrides name what the profile does not have, as
            `Overrides.laid_over` says.
        ReportError: The file cannot be written.
    """
    content = render(profile, overrides).encode("utf-8")
    try:
        write_whole(path, content)
    except OSError as error:
        raise ReportError(f"{path} cannot be written: {error.strerror}") from error
