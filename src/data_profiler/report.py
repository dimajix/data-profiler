"""The stage report: a profile rendered as one HTML document, which a browser shows on its own.

The document holds its styles inside, and no script, so that it can be sent and printed as it is. It
shows the profile with the overrides of the project laid over it: what the database holds, where it
is given; each table, with the reading of its name, what it holds, where it is given, and with its
columns - their original names, harmonized names, composed from their readings or given, readings,
each term with the word of its concept, descriptions, types, statistics, the shares of their nulls
and sentinels among them, those of no information, filled in no row, marked as such, semantic types,
sensitivity, the values of their enumerations, the first few of those of nothing but UUIDs, and each
of their sentinels -, with its keys, the primary marked, and whether it is given, a table of the
references of its columns, one to one or many to one, their coverage and whether they are given, the
reference candidates of each column ranked, a table of the references of others to it, of the same,
and a diagram of the tables connected to it by their original names, those by reference candidates
alone dashed, the column groups of its columns filled together, its column dependencies, each
determinant marked where it is a reference, the harmonized names two of its columns share, and its
entities, by the share of their rows each column is filled in, with their names and descriptions,
where they are given; and the glossary, each concept with its abbreviations and description, those
proposed told apart from those given, and each term of no concept, as describe split the names, with
where it appears. It renders what the profile holds, and nothing of the workspace: the values in it
are those the profile may hold, which the template escapes.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import Final

from jinja2 import Environment, PackageLoader, StrictUndefined

from data_profiler.detect import UUID
from data_profiler.diagram import Diagram, lay_out
from data_profiler.files import write_whole
from data_profiler.glossary import Glossary, agrees, unknown
from data_profiler.overrides import Overrides
from data_profiler.profile import Findings, Profile, Reference, Table

# The places a term of no concept is shown with, before the number of the others.
_PLACES: Final = 8

# The values listed of a column of nothing but UUIDs, any one of which looks like the next.
_UUIDS: Final = 5

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
        glossary=glossary,
        harmonized=glossary.harmonized,
        agrees=agrees,
        collisions=glossary.collisions,
        reference_candidates=_reference_candidates,
        diagram=_diagram,
        limit=_limit,
    )


def _limit(found: Findings) -> int | None:
    """The most values of `found` to list: a few of nothing but UUIDs, else None, for all of them.

    Nothing but UUIDs is all of the sample, and all of the table where the table was verified, by
    the shares as the profile rounds them and the report shows them.
    """
    uuids = any(
        match.type == UUID and match.sample == 1 and match.table in (None, 1)
        for match in found.matches
    )
    return _UUIDS if uuids else None


def _reference_candidates(table: Table) -> dict[str, list[Reference]]:
    """The reference candidates of `table`, by their columns, in their order and ranks."""
    found: dict[str, list[Reference]] = {}
    for reference in table.reference_candidates:
        found.setdefault(reference.column, []).append(reference)
    return found


def _diagram(profile: Profile, table: Table) -> Diagram | None:
    """The diagram of the tables connected to `table`, or None where none is."""
    coming = _connected(
        (other.name for other, _ in profile.referring(table.name)),
        (other.name for other, _ in profile.candidates_referring(table.name)),
    )
    going = _connected(
        (reference.table for reference in table.references),
        (reference.table for reference in table.reference_candidates),
    )
    coming.pop(table.name, None)
    itself = going.pop(table.name, None)
    if not coming and not going and itself is None:
        return None
    return lay_out(table.name, coming, going, itself)


def _connected(references: Iterable[str], candidates: Iterable[str]) -> dict[str, bool]:
    """Whether each table is connected by reference candidates alone, those of references first."""
    connected = dict.fromkeys(references, False)
    return connected | {name: True for name in candidates if name not in connected}


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
