"""The files the tool writes: whole or not at all, under names that every system takes.

A file is written whole, so that a failure leaves the file that was there before. The names of
tables become names of files, of the profile and of the workspace alike; the profile is shared to
other systems by version control, so a name is one only where every system takes it.
"""

import re
from pathlib import Path
from typing import Final
from uuid import uuid4

# The characters no name of a file holds on one of the systems: the separators of directories, those
# Windows refuses, and the control characters.
_REFUSED: Final = re.compile(r'[/\\<>:"|?*\x00-\x1f]')
# The names Windows reserves for its devices, with whatever extension, in any case.
_RESERVED: Final = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"{device}{n}" for device in ("COM", "LPT") for n in range(1, 10)]
)


def write_whole(path: Path, content: bytes) -> None:
    """Replaces the file `path` by `content`, whole or not at all.

    The content is written to a new file next to `path`, which then takes its place, so that a
    failure, or an interruption, leaves the file that was there before. The new file is made as
    any file is, with the permissions the user gives new files.

    Args:
        path: The file to write.
        content: What it is to hold.

    Raises:
        OSError: The file cannot be written.
    """
    temporary = path.with_name(f".{path.name}.{uuid4().hex}")
    try:
        with temporary.open("xb") as file:
            file.write(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def is_file_name(name: str) -> bool:
    """Whether `name`, with an extension, is the name of a file in its directory on every system.

    Args:
        name: The name, such as the name of a table.

    Returns:
        False where it is empty, begins with `.` - which would hide it, or leave its directory as
        `..` -, holds a separator of directories or a character Windows refuses, or is a name
        Windows reserves, such as `con`; True else.
    """
    return (
        bool(name)
        and not name.startswith(".")
        and _REFUSED.search(name) is None
        and name.split(".")[0].upper() not in _RESERVED
    )
