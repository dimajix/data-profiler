"""The stage relate: the references between the tables of a profile, found on its source.

It reads the profile `scan` wrote, of the schema of the source, and finds the references of its
tables to the keys of each other by the module `references`, which queries the database; the
profile is written once, at the end, with the references and candidates of every table in place of
those it had, so that a relate that fails leaves it as it was, and the next one begins anew.
"""

import logging
from pathlib import Path

from data_profiler.profile import Profile
from data_profiler.references import find
from data_profiler.source import Source

_logger = logging.getLogger(__name__)


def relate(source: Source, directory: Path) -> None:
    """Relates the tables of the profile in `directory` to the keys of each other, by `source`.

    Args:
        source: The schema of the profile.
        directory: The directory of the profile, which scan wrote.

    Raises:
        ProfileError: The profile cannot be read, is of another schema than `source`, or cannot be
            written.
        SourceError: The database fails to probe the references or to count their coverage.
    """
    profile = Profile.read_of(directory, source.catalog, source.schema)
    _logger.info("Relating the %d tables of %s", len(profile.tables), directory)
    find(source, profile).write(directory)
