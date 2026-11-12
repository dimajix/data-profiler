"""Tests of the templates of the stage export: what `Template.write` does for every template."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from data_profiler.export import ExportError, Template
from data_profiler.overrides import Overrides
from data_profiler.profile import Concept, Profile


class _Given(Template):
    """A template of the files given, which keeps the profiles and overrides it is given."""

    name = "given"

    def __init__(self, files: Mapping[str, bytes]) -> None:
        self.given: list[tuple[Profile, Overrides]] = []
        self._files = files

    def files(self, profile: Profile, overrides: Overrides) -> Mapping[str, bytes]:
        self.given.append((profile, overrides))
        return self._files


def test_the_files_of_a_template_are_written_into_its_directory_made_where_it_does_not_exist(
    tmp_path: Path, example_profile: Profile
) -> None:
    directory = tmp_path / "export" / "given"
    _Given({"one.txt": b"one", "two.txt": b"two"}).write(example_profile, Overrides(), directory)
    assert (directory / "one.txt").read_bytes() == b"one"
    assert (directory / "two.txt").read_bytes() == b"two"


def test_a_template_is_given_the_profile_with_the_overrides_laid_over_and_the_overrides(
    tmp_path: Path, example_profile: Profile
) -> None:
    template = _Given({})
    overrides = Overrides(description="A CRM.")
    template.write(example_profile, overrides, tmp_path)
    [(profile, given)] = template.given
    assert profile.description == "A CRM.", "the overrides are laid over"
    assert given is overrides


def test_an_abbreviation_given_that_no_name_has_is_warned_of(
    tmp_path: Path, example_profile: Profile, caplog: pytest.LogCaptureFixture
) -> None:
    overrides = Overrides(glossary={"order": Concept(("xqz",))})
    _Given({}).write(example_profile, overrides, tmp_path)
    assert caplog.messages == [
        "The overrides give abbreviations, in lower case as terms are, that no name of the profile"
        " has: xqz"
    ]


def test_a_template_whose_directory_cannot_be_made_is_refused(
    tmp_path: Path, example_profile: Profile
) -> None:
    (tmp_path / "export").write_text("a file, not a directory", encoding="utf-8")
    with pytest.raises(ExportError, match="cannot be written"):
        _Given({}).write(example_profile, Overrides(), tmp_path / "export" / "given")


def test_a_file_that_cannot_be_written_is_refused(tmp_path: Path, example_profile: Profile) -> None:
    (tmp_path / "one.txt").mkdir()
    with pytest.raises(ExportError, match=r"one\.txt cannot be written"):
        _Given({"one.txt": b"one"}).write(example_profile, Overrides(), tmp_path)
