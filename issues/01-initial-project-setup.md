# 01 — Initial project setup

**Status:** open
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
