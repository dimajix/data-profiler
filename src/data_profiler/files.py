"""Files written whole or not at all, so that a failure leaves the file that was there before."""

from pathlib import Path
from uuid import uuid4


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
