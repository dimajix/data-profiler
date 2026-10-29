"""Tests that every module of the project, its tests included, begins with one sentence.

That a module has a description, and its layout, ruff checks (`D100`, `D104`, `D205`); whether its
first sentence names the module's responsibility, only a reader can judge. A full stop followed by
a space ends a sentence.
"""

import ast
import re
import tomllib
from pathlib import Path

import pytest

_TOP = Path(__file__).parent.parent
_CONFIGURATION = tomllib.loads((_TOP / "pyproject.toml").read_text(encoding="utf-8"))
# The directories of code are those mypy checks, to which every new one is added.
_SOURCES = _CONFIGURATION["tool"]["mypy"]["files"]
_MODULES = sorted(module for source in _SOURCES for module in (_TOP / source).rglob("*.py"))


@pytest.mark.parametrize("module", _MODULES, ids=lambda module: str(module.relative_to(_TOP)))
def test_the_first_paragraph_of_a_module_description_is_one_sentence(module: Path) -> None:
    description = ast.get_docstring(ast.parse(module.read_text(encoding="utf-8")))
    assert description is not None, "the module has no description"
    first = description.split("\n\n")[0].strip()
    sentences = re.split(r"(?<=\.)\s+", first)
    assert len(sentences) == 1 and first.endswith("."), f"not one sentence: {first!r}"
