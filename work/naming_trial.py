"""A trial of issue 04: whether a small local language model names columns from prepared facts.

It plays the stage `describe` by hand, on an environment that `scan` has profiled: first it asks the
model, through Ollama with a JSON schema as `format`, for the word of each term of the names of the
columns chosen, shown the tables and columns the term appears in; then for the name and description
of each column, given the words. The facts come from the profile, the overrides laid over it, and
the samples of the workspace; the database is not asked. The answers, with the time each took and
an empty judgement for the person who judges them, are written into the workspace, which never
leaves the machine; `--summary` counts the judgements, which alone go into the issue.

    uv run python work/naming_trial.py ENVIRONMENT [--project DIR] --model MODEL [--columns T.C,...]
    uv run python work/naming_trial.py ENVIRONMENT [--project DIR] --summary

It is a trial, not a part of the tool: what holds is built into `describe` by issue 10.
"""

import json
import logging
import os
import re
import time
import urllib.request
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from yaml import safe_dump, safe_load

from data_profiler.commands import run
from data_profiler.glossary import harmonized, occurrences, terms
from data_profiler.overrides import Overrides, OverridesError
from data_profiler.profile import Column, Profile, ProfileError, Table
from data_profiler.project import Project, ProjectError
from data_profiler.source import as_text
from data_profiler.workspace import Sample, Workspace, WorkspaceError

_logger = logging.getLogger(__name__)

_SHOWN: Final = (ProjectError, ProfileError, OverridesError, WorkspaceError)

# The values of a sample shown of a column, and the neighbours shown on either side of it.
_SAMPLES: Final = 5
_NEIGHBOURS: Final = 3

_WORD: Final = {
    "type": "object",
    "properties": {"word": {"type": "string"}},
    "required": ["word"],
}
_SUGGESTION: Final = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
    "required": ["name", "description"],
}

_TERM_PROMPT: Final = """\
You help to document the tables of a CRM database whose names are made of English abbreviations.
The abbreviation "{term}" appears in these names of tables and columns, each column with its
type, what it was recognised as, and a few of its values:

{places}

Which English word, or few words, does "{term}" stand for in all of them? An abbreviation is mostly
the word shortened, its letters in the order of the word: "cd" for "code", "qty" for "quantity".
Answer with the word alone, in lower case, without the abbreviation.
"""

_COLUMN_PROMPT: Final = """\
You help to document the tables of a CRM database whose names are made of English abbreviations.
Here is what is known of the column "{column}" of the table "{table}":

{facts}

The abbreviations of its name stand for: {words}.
Composed of them, its name would be "{composed}".

Give the column a name in English snake_case - the composed one, or a better one - and a
description of one or two sentences of what it holds, for a person who knows the business but not
the database.
"""


def main() -> None:
    """Runs the trial, or counts its judgements."""
    parser = ArgumentParser(prog="naming_trial", description="The trial of issue 04.")
    parser.add_argument("environment", help="the name of the environment, profiled by scan")
    parser.add_argument("--project", type=Path, default=Path(), help="the directory of the project")
    parser.add_argument("--model", help="the model of Ollama to ask")
    parser.add_argument("--columns", help="the columns to name, as table.column, by commas")
    parser.add_argument(
        "--ollama",
        default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        help="where Ollama answers (default: $OLLAMA_HOST, else http://localhost:11434)",
    )
    parser.add_argument(
        "--think", action="store_true", help="let a model that can think before it answers do so"
    )
    parser.add_argument("--summary", action="store_true", help="count the judgements")
    parser.add_argument("--debug", action="store_true", help="log at debug level")
    arguments = parser.parse_args()
    if arguments.summary:
        run(lambda: _summary(arguments.project, arguments.environment), arguments.debug, _SHOWN)
    elif arguments.model:
        run(lambda: _trial(arguments), arguments.debug, _SHOWN)
    else:
        parser.error("either --model or --summary is needed")


def _trial(arguments: Any) -> None:
    """Asks the model for the words of the terms and the names of the columns, and writes them."""
    project = Project.read(arguments.project, os.environ)
    environment = project.environment(arguments.environment)
    profile = Overrides.read(project.overrides).laid_over(Profile.read(environment.profile))
    workspace = Workspace.open(environment.workspace, profile.catalog, profile.schema)
    wanted = set(arguments.columns.split(",")) if arguments.columns else None
    chosen = [
        (table, column)
        for table in profile.tables
        for column in table.columns
        if wanted is None or f"{table.name}.{column.name}" in wanted
    ]
    samples = {table.name: workspace.read_sample(table.name) for table in profile.tables}
    columns = {
        f"{table.name}.{column.name}": (table, column)
        for table in profile.tables
        for column in table.columns
    }

    places = occurrences(profile)
    needed = {term for _, column in chosen for term in terms(column.name) if term in places}
    words: dict[str, str] = dict(profile.glossary)
    answers: dict[str, Any] = {"model": arguments.model, "terms": {}, "columns": {}}
    for term in sorted(needed - set(words)):
        shown = "\n".join(
            f"- {place}{_brief(columns[place], samples)}" if place in columns else f"- {place}"
            for place in places[term][:20]
        )
        prompt = _TERM_PROMPT.format(term=term, places=shown)
        answer, seconds = _ask(arguments, prompt, _WORD)
        words[term] = str(answer.get("word", "")).strip()
        answers["terms"][term] = {"word": words[term], "seconds": seconds, "judgement": None}
        _logger.info("Asked for the word of a term: %.1f s", seconds)

    for table, column in chosen:
        facts = _facts(table, column, samples[table.name].columns.get(column.name, []))
        named = {term: words.get(term, "?") for term in terms(column.name)}
        prompt = _COLUMN_PROMPT.format(
            column=column.name,
            table=table.name,
            facts=facts,
            words=", ".join(f'"{term}" for "{word}"' for term, word in named.items()),
            composed=harmonized(column.name, words) or "-",
        )
        answer, seconds = _ask(arguments, prompt, _SUGGESTION)
        answers["columns"][f"{table.name}.{column.name}"] = {
            "name": str(answer.get("name", "")),
            "description": str(answer.get("description", "")),
            "seconds": seconds,
            "judgement": None,
        }
        _logger.info("Asked for the name of a column: %.1f s", seconds)

    path = _trials(environment.workspace) / f"{re.sub(r'[^\w.-]', '_', arguments.model)}.yml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(safe_dump(answers, sort_keys=False, allow_unicode=True), encoding="utf-8")
    _logger.info("Wrote the answers of %s to %s", arguments.model, path)


def _brief(found: tuple[Table, Column], samples: dict[str, Sample]) -> str:
    """The type of a column, what it was recognised as, and a few of its values, in parentheses."""
    table, column = found
    values = samples[table.name].columns.get(column.name, [])
    shown = list(dict.fromkeys(as_text(value) for value in values if value is not None))[:3]
    parts = [column.type, *(f"recognised as {match.type.value}" for match in column.matches)]
    if shown:
        parts.append("values: " + ", ".join(shown))
    return f" ({'; '.join(parts)})"


def _facts(table: Table, column: Column, values: Sequence[object]) -> str:
    """What is known of `column` of `table`, as lines of text, its sample among them."""
    statistics = column.statistics
    index = [c.name for c in table.columns].index(column.name)
    neighbours = [
        c.name for c in table.columns[max(0, index - _NEIGHBOURS) : index + 4] if c != column
    ]
    shown = list(dict.fromkeys(as_text(value) for value in values if value is not None))[:_SAMPLES]
    lines = [
        f"- type: {column.type}",
        f"- rows of the table: {table.rows}, of them null: {statistics.nulls}",
        f"- distinct values: {statistics.distinct}",
        f"- columns beside it: {', '.join(neighbours)}",
    ]
    if statistics.lengths:
        lines.append(f"- lengths: {statistics.lengths.shortest} to {statistics.lengths.longest}")
    if column.values:
        counted = ", ".join(f"{value.value} ({value.rows})" for value in column.values[:20])
        lines.append(f"- its values, with their rows: {counted}")
    if column.matches:
        found = ", ".join(f"{match.type.value} ({match.sample:.0%})" for match in column.matches)
        lines.append(f"- recognised as: {found}")
    if shown:
        lines.append(f"- a few of its values: {', '.join(shown)}")
    return "\n".join(lines)


def _ask(arguments: Any, prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], float]:
    """The answer of the model to `prompt`, in the form of `schema`, and the seconds it took.

    A model that can think does not, unless asked to: thinking, a model of 1.7 billion parameters
    took minutes for one word, and found it no better.
    """
    body = {
        "model": arguments.model,
        "messages": [{"role": "user", "content": prompt}],
        "format": schema,
        "stream": False,
        "think": arguments.think,
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        f"{arguments.ollama.rstrip('/')}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.loads(response.read())
    seconds = round(time.monotonic() - start, 1)
    try:
        return json.loads(reply["message"]["content"]), seconds
    except (KeyError, json.JSONDecodeError):
        _logger.warning("An answer of %s was no JSON of the form asked for", arguments.model)
        return {}, seconds


def _summary(directory: Path, name: str) -> None:
    """Counts the judgements of the answers of each model, and the time they took."""
    environment = Project.read(directory, os.environ).environment(name)
    for path in sorted(_trials(environment.workspace).glob("*.yml")):
        answers = safe_load(path.read_text(encoding="utf-8"))
        for kind in ("terms", "columns"):
            found = list(answers.get(kind, {}).values())
            judged = [answer.get("judgement") for answer in found]
            counts = {verdict: judged.count(verdict) for verdict in ("right", "usable", "wrong")}
            seconds = sum(answer.get("seconds", 0) for answer in found)
            _logger.info(
                "%s, %s: %d answers, %d right, %d usable, %d wrong, %d not judged, %.0f s in all",
                answers.get("model"),
                kind,
                len(found),
                counts["right"],
                counts["usable"],
                counts["wrong"],
                judged.count(None),
                seconds,
            )


def _trials(workspace: Path) -> Path:
    """The directory of the answers of the trial, in the workspace, which keeps itself private."""
    return workspace / "trials"


if __name__ == "__main__":
    main()
