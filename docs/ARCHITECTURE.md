# Architecture

This document draws the overall picture of the project - what the parts are, how they work
together, and the principles the design follows. Every section ends with the document that holds
the details, where there is one; the list at the end names them all.

> **TODO (issue 01):** Name the project in the heading and say in two or three sentences what it is.
> Fill in the sections marked below; a section with nothing to say yet is left out rather than kept
> empty.

## Parts

> **TODO (issue 01):** The packages, modules or crates of the project, one entry each: its name and,
> in one sentence, what it owns - the test of
> [one owner per concern](../AGENTS.md#design-principles). Which part depends on which.

## The domain

> **TODO (issue 01):** The concepts of the project, each under the one name it has in the code and
> in the documents ([concepts are named](../AGENTS.md#design-principles)), and how they relate to
> each other.

## How it works

> **TODO (issue 01):** How the parts work together - the way a request, a message or a piece of data
> travels through them, from where it enters to where it ends.

## Principles

The design repeats a few decisions; new code follows them.

> **TODO (issue 01):** The decisions the design repeats, one bold sentence each with its reason -
> who decides what, who writes which data, what is never done. They are added as they are made; at
> the start there may be none.

## The repository

*   **`docs/`** - the documents of the project: this one, the
    [coding guidelines](CODING-GUIDELINES.md) and one document per subject that outgrew its section
    here (see the list below).
*   **`issues/`** - the issues, one file each, and the overviews generated from them (see
    [issues/README.md](../issues/README.md)).
*   **`scripts/`** - the tools that check the rules of the documents, such as
    `scripts/wrapping.sh`.
*   **`.githooks/`** - the pre-commit hook, which runs those checks and keeps the issue overviews up
    to date; enabled per clone with `git config core.hooksPath .githooks`.
*   **`.claude/agents/`** - the agents Claude Code is given for the workflow of
    [AGENTS.md](../AGENTS.md#workflow), such as the `reviewer`.
*   **`AGENTS.md`** - how we work together; `CLAUDE.md` points Claude Code to it, and the links
    `.cursorrules` and `.clinerules` point Cursor and Cline to it.

## Documents

*   [CODING-GUIDELINES.md](CODING-GUIDELINES.md) - coding style, error handling, logging, tests,
    and the checks that run before every commit.
