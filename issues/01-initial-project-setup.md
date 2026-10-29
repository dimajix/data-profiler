# 01 — Initial project setup

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Tooling and process
**Summary:** The repository is still the generic project template: its documents, checks and issue areas say nothing yet about this project, its language or its tools.

## The problem

The repository was made from a project template. It brings the rules of how we work together
([AGENTS.md](../AGENTS.md)), the keeping of issues in this directory, the documents in `docs/`, the
wrapping check `scripts/wrapping.sh` and the pre-commit hook in `.githooks` - all of them written
for any project and any language. What only this project can say is missing: what it is, what it is
written in, how it is built, tested and checked, and which subjects its issues fall into.

Every place still to be filled carries the marker `TODO (issue 01)`;
`git grep -n "TODO (issue 01)" -- ":!issues/01-*"` lists them.

## Why it matters

The workflow of AGENTS.md rests on these places: an agent reads ARCHITECTURE.md to find where a
change belongs, runs the checks of CODING-GUIDELINES.md before every report, and sorts every new
issue into an area. As long as they are templates, each of these steps is guessed at.

## What is to be decided

With the maintainer, before anything is written - each question laid out with its options and a
recommendation, as [AGENTS.md](../AGENTS.md#decisions) asks:

1.  **The project.** Its name, what it is for and for whom, its main features -
    `README.md` and the opening of `docs/ARCHITECTURE.md`.
2.  **The language and the layout.** The language or languages, the build tool, and the parts of
    the repository - packages, modules, crates - with what each owns: "Parts" in
    `docs/ARCHITECTURE.md`. Where the domain is known already, its concepts under their names: "The
    domain".
3.  **The checks.** The commands that run the tests, the formatter and the linter: the table
    "Checks" in `docs/CODING-GUIDELINES.md`, the formatter and the linter also in
    `.githooks/pre-commit`; the build and the tests also in `README.md`. Which lints are turned on
    to check rules of the guidelines, in the linter's configuration.
4.  **The rules of the language.** Each rule of `docs/CODING-GUIDELINES.md` that depends on the
    language gets its form in it: error types, the logging library, how visibility is narrowed,
    where tests and shared fixtures live. A rule that does not apply is deleted.
5.  **The wrapping.** Which files `scripts/wrapping.sh` covers (`is_covered`) and the comment
    markers of the project's languages (`slash`, `block`, `hash`); the 100 characters, unless the
    language's formatter keeps code narrower and comments should follow it.
6.  **The areas of issues.** The subjects the issues of this project fall into, in the order of
    their sections: the list in `issues/generate.sh` and in `issues/README.md`.
7.  **The license.** Which, and its files in the repository - `README.md`, "License".
8.  **Further documents.** None at the start: a subject gets a document of its own once it outgrows
    its section in `docs/ARCHITECTURE.md` (see [AGENTS.md](../AGENTS.md#documentation)).

## How

On a branch `issue-01-initial-project-setup`, as [AGENTS.md](../AGENTS.md#workflow) describes: the
questions above first, then the documents, the scripts and the hook filled in step by step, each
step reported to the maintainer. A `.gitignore` for the language's build output comes with the
second question. The marker `TODO (issue 01)` is removed with what it asks for, together with the
remarks of the template that no longer say anything once filled in.

## Done when

- `git grep -n "TODO (issue 01)" -- ":!issues/01-*"` finds nothing.
- `README.md` says what the project is and how it is built, tested and run, under its name.
- `docs/ARCHITECTURE.md` names the parts of the project and what each owns.
- `docs/CODING-GUIDELINES.md` names the language and the commands of every check, and gives the
  rules that depend on the language their form in it.
- `.githooks/pre-commit` runs the formatter and the linter, and a commit of code passes it.
- `issues/generate.sh` and `issues/README.md` list the areas of this project, and
  `issues/generate.sh --check` passes.
- `scripts/wrapping.sh` covers the sources of the project and passes on every file it covers.

## History

- **2026-10-29** — Opened with the template, whose rules and tools are taken from an existing
  project and written for any language.

- **2026-10-29** — Questions 1 and 2 decided with the maintainer, recorded in `README.md` and
  `docs/ARCHITECTURE.md`. The project stays `data-profiler`: a command line tool for data engineers
  that profiles the tables of a Trino or Starburst database - a CRM of about 20 tables of up to 200
  columns is the first case - and proposes readable, harmonized English names for its columns.
  What was weighed:
  - *Stages.* One run doing everything, or the stages `scan`, `describe` and `report` sharing
    nothing but the profile and the workspace: chosen the stages, so that the language model can be
    run again without querying the database, and every stage but `scan` can be tested without one.
    The price is that the profile's format is a contract.
  - *Sensitive data.* The data must not reach an external language model, and the profile must
    hold nothing under GDPR or PCI; the local model may see values. Hence the profile holds raw
    values only for columns no detector marks as sensitive, never the range of texts, and samples
    go into a workspace that keeps itself out of version control - an entry in this repository's
    `.gitignore` would not protect a workspace elsewhere.
  - *Where things are counted.* The maintainer proposed distinct counts on a sample, to spare the
    database a `GROUP BY` on columns such as UUIDs. Chosen instead: `approx_distinct` on the whole
    table, which needs constant memory, and an exact `GROUP BY` only below the enum threshold - a
    sample would distort the very count that tells an enum. Detectors check a sample in code
    (checksums, phone number rules) and verify their findings on the whole table by a pattern in
    SQL, as the maintainer proposed.
  - *Semantics and names.* The language model alone, or deterministic detectors deciding the type
    and the model only naming: chosen the latter, since a model of 1 to 2 billion parameters names
    well from prepared facts but does not reason reliably. Names are composed from a glossary of
    the terms of the original names - mostly abbreviations -, so that one term reads the same
    everywhere and one correction fixes every column; corrections are overrides, a part of a
    profile laid over it, not a format of their own.
  - *Other databases.* Kept open by a dialect that writes all SQL, not by an abstraction no second
    database uses yet.
  - *Language and layout.* Python 3.13, for its Trino client, `sqlglot` and the libraries for
    detectors and reports; Rust and the JVM were weighed and lack them. The test data generator is
    a project of its own in a uv workspace rather than a second package of the tool, so that the
    tool's package carries neither it nor its dependencies. The tool is run from a clone on the
    target machine, which runs Windows.
  - *Simulation.* There is no access to Starburst where the tool is developed: a Trino in Docker,
    with a PostgreSQL catalog for fast loading, and Ollama under a compose profile of its own,
    since Ollama already runs on the development machine and would collide with it.

- **2026-10-29** — Question 3 decided: `pytest` for the tests, `ruff` as formatter and linter,
  `mypy` in its strict mode for the types - pyright was weighed and offers nothing more here -, with
  doc comments in the Google convention; the formatter, the linter and `mypy` run in the pre-commit
  hook. The lints that check rules of the guidelines are turned on in `pyproject.toml`; the rules
  name them with question 4. An exception of a named type that is passed over counts as dropped too,
  and `SIM105` is turned off: it proposes `contextlib.suppress`, which drops it all the same. Tests
  that need the simulation environment run like every other test: the maintainer starts the
  environment beforehand, and it is reachable on `localhost` from where the agents run, which cannot
  start containers themselves. A marker deselecting them was weighed and is not needed; skipping
  them when the environment is down was rejected, since a skipped test hides that nothing was
  checked.

- **2026-10-29** — Question 4 decided: every rule of `docs/CODING-GUIDELINES.md` has its form in
  Python, and names its lint where one checks it (`TID252`, `SLF001` and `S112` are new, and
  `TID251` bans the APIs only `cli` may use, and `typing.Protocol`). Interfaces between parts are
  abstract classes rather than protocols, so that an implementation says what it implements.
  "Rolling back" became "Files are written whole", since the tool never writes to the database. The
  command line reports its progress through the log, so that nothing prints; values of the database
  are logged at `debug` alone; the rule on ids in spans was deleted, as it belongs to a service, not
  a command line; and error messages may name files and paths, since they are read on the machine of
  the user. The first test checks a part of the rule on module descriptions that ruff does not
  check: that the first paragraph is one sentence. The review found that the cause of a database
  error may carry a value of the database - `Cannot cast 'Müller' to INTEGER` - and with it the
  traceback. Weighed: a database error reduced to its name and query id, its message cut off, so
  that no value is ever logged; or values of the database at `debug`. The maintainer chose the
  latter: the log stays on the machine, as the workspace does.

- **2026-10-29** — Question 5 decided: prose wraps at 100 characters, as ruff's `line-length`.
  `scripts/wrapping.sh` covers `README.md` and the hooks in `.githooks/` as well, but not
  `CLAUDE.md`, which only points to `AGENTS.md`. It knows the comments of the project's languages
  only - `py`, `sh`, `toml`, `yml` and `yaml`; a language is added once the project has a file of
  it. The lists of the comment markers `//` and `/*` stay, empty, with what reads them: the HTML
  reports will bring style sheets and scripts, and removing the mechanism now would mean writing it
  again then. The script now checks the docstrings of Python too, which are its doc comments: ruff
  checks their length (`E501`), but nothing checked the rule on dashes. A docstring is told apart
  from another string by where it stands, after the header of a definition or at the top of its
  module, and by its first line, which begins with `"""` and its summary, as ruff checks with
  `D212`. The review found that a dash on the hanging indent of an entry under `Args:` went
  unchecked; a dash further in than the prose of the line before now counts as well. A code block
  left open in a comment no longer turns off the checks for the rest of the file.

- **2026-10-29** — Question 6 decided: the areas of issues are the parts of the tool, in the order
  of the parts in `docs/ARCHITECTURE.md` - Profile, Scan, Detection, Describe, Report, Command line,
  Simulation -, and Architecture and Tooling and process across them. The generic areas of the
  template were dropped: a feature, a test or a document belongs to the part it is about, and
  "Features" would have held most issues.

- **2026-10-29** — Question 7 decided: the Apache License, Version 2.0, as Flowman has it, in
  `LICENSE` and in both `pyproject.toml`. Question 8: no further documents at the start. Done: no
  `TODO (issue 01)` is left, and every check passes. `README.md` says how the project is built and
  tested; how the tool is run, and what the simulation environment and Ollama are needed for, it
  says once they exist. The final review found that `yml` and `yaml`, decided with question 5, broke
  the rule decided with them - a language is added once the project has a file of it -, so they were
  left out until the first such file; and that the order of the areas was not the order of the parts
  in `docs/ARCHITECTURE.md`, so the parts were put in the order of the areas.
