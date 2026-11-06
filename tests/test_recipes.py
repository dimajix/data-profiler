"""Tests of the recipes of docs/PROJECT.md: each snippet read as its file, and laid over."""

import re
from pathlib import Path
from typing import Final

import pytest

from data_profiler import overrides, project
from data_profiler.overrides import Overrides
from data_profiler.profile import Profile
from data_profiler.project import Project

_TOP: Final = Path(__file__).parents[1]
_RECIPES: Final = re.findall(
    r"^```yaml (project\.yml|overrides\.yml)\n(.*?)^```$",
    (_TOP / "docs" / "PROJECT.md").read_text(encoding="utf-8"),
    re.MULTILINE | re.DOTALL,
)
_PROFILE: Final = _TOP / "simulation" / "profiles" / "crm"


def _written(directory: Path, file: str, snippet: str) -> Path:
    """The snippet written as `file` in `directory`, with the version of its format first."""
    version = (project.FORMAT if file == "project.yml" else overrides.FORMAT).version
    path = directory / file
    path.write_text(f'format: "{version}"\n{snippet}', encoding="utf-8")
    return path


def test_the_document_holds_recipes_of_both_files() -> None:
    files = {file for file, _ in _RECIPES}
    assert files == {"project.yml", "overrides.yml"}, "the snippets are found by their files"


@pytest.mark.parametrize(
    "snippet",
    [snippet for file, snippet in _RECIPES if file == "project.yml"],
    ids=lambda snippet: snippet.splitlines()[0],
)
def test_a_recipe_of_the_configuration_is_read(tmp_path: Path, snippet: str) -> None:
    _written(tmp_path, "project.yml", snippet)
    Project.read(tmp_path, {})


@pytest.mark.parametrize(
    "snippet",
    [snippet for file, snippet in _RECIPES if file == "overrides.yml"],
    ids=lambda snippet: snippet.splitlines()[0],
)
def test_a_recipe_of_the_overrides_is_laid_over_the_example_profile(
    tmp_path: Path, snippet: str
) -> None:
    given = Overrides.read([_written(tmp_path, "overrides.yml", snippet)])
    given.laid_over(Profile.read(_PROFILE))
