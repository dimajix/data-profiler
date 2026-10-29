"""Tests of files written whole or not at all."""

from pathlib import Path

import pytest

from data_profiler.files import write_whole


def test_a_file_written_whole_holds_its_content(tmp_path: Path) -> None:
    path = tmp_path / "file"
    write_whole(path, b"one")
    write_whole(path, b"two")
    assert path.read_bytes() == b"two"
    assert [file.name for file in tmp_path.iterdir()] == ["file"], "no temporary file is left"


def test_a_file_that_cannot_be_written_leaves_what_was_there(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.mkdir()
    with pytest.raises(OSError):
        write_whole(path, b"one")
    assert path.is_dir(), "what was there before is left as it was"
    assert [file.name for file in tmp_path.iterdir()] == ["file"], "no temporary file is left"
