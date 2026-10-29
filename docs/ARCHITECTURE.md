# Architecture of data-profiler

This document draws the overall picture of the project - what the parts are, how they work
together, and the principles the design follows. Every section ends with the document that holds
the details, where there is one; the list at the end names them all.

data-profiler is a command line tool for data engineers that profiles the tables of an SQL
database - Trino and Starburst first - to help build an understandable data model of it: what each
column contains, and a harmonized name for it, composed from one glossary for the whole database.
It reads the database through generated SQL, recognises the semantic types of columns with
deterministic detectors, and asks a small local language model for names; no value leaves the
machine it runs on.

The project is at its beginning: the parts below are the design it is built to, and come into the
code one by one.

## Parts

The tool is one Python package, `data_profiler`, in `src/`. The test data generator is a project of
its own, `simulation`, in `simulation/`: it uses the tool's profile, but the tool does not depend on
it, nor on what it needs. Both are one uv workspace, with one lock file and one environment.

*   **`data_profiler.profile`** - the profile: its schema, reading and writing it as YAML, and
    laying overrides over it.
*   **`data_profiler.source`** - the database: the `Source`, which connects and runs queries, and
    the `Dialect`, which writes every SQL statement the tool sends.
*   **`data_profiler.detect`** - the semantic types, their sensitivity, and the detectors that
    recognise them.
*   **`data_profiler.workspace`** - the workspace: the local directory of samples and intermediate
    results, which never leaves the machine.
*   **`data_profiler.scan`** - the stage `scan`: statistics, enums, samples and detector matches of
    the selected tables, written to a profile.
*   **`data_profiler.glossary`** - splitting original names into terms, and composing harmonized
    names from the words of the glossary.
*   **`data_profiler.describe`** - the stage `describe`: the glossary's words and the columns'
    names and descriptions, proposed by the language model.
*   **`data_profiler.report`** - the stage `report`: the profile rendered as HTML.
*   **`data_profiler.cli`** - the command line: arguments, `.env`, and running the stages.
*   **`simulation`** - test data: tables generated from a profile and loaded into the simulation
    environment - Trino with a PostgreSQL catalog, and Ollama under a compose profile of its own -,
    for tests and for trying the tool without access to the real database.

The stages read and write the profile: `scan` uses `source`, `detect` and `workspace`, `describe`
uses `glossary` and `workspace`, `report` the profile alone; `cli` runs the stages.

## The domain

*   **Stage** - one of `scan`, `describe` and `report`: a step of the work that can be run on its
    own, from what the stages before it left.
*   **Source** - the database the tool reads, by its URL; **Dialect** - the SQL of one kind of
    database.
*   **Profile** - the document describing one database: its tables and columns, what was found
    about them, and the glossary. It is the only thing the stages hand to each other besides the
    workspace, and it holds no sensitive values (see [Principles](#principles)).
*   **Table** and **Column** - as found in the database, under their original names.
*   **Statistics** - what is counted of a column on the whole table: rows, nulls, the approximate
    number of distinct values, the range of numbers and dates, the range of lengths of texts.
*   **Enum** - a column with few distinct values, below a threshold; its values with their
    frequencies.
*   **Sample** - rows taken from a table at random, kept in the workspace.
*   **Semantic type** - what the values of a column are: a phone number, an IBAN, a date. Each has
    a **sensitivity**: personal data (GDPR), payment card data (PCI), or none.
*   **Detector** - recognises one semantic type: in the values of a sample, precisely, and where it
    can, on the whole table by a pattern in SQL.
*   **Match** - a semantic type found in a column, with the share of values that match it in the
    sample and, once verified, in the whole table.
*   **Term** - a part of the original names, mostly an abbreviation: `CUST` in `CUST_CRT_DT`.
*   **Glossary** - the word each term of the database stands for, once for the whole database:
    `customer` for `CUST`.
*   **Suggestion** - the harmonized name and the description proposed for a column, in English, the
    name composed from the words of the glossary.
*   **Override** - a part of a profile, written by hand, laid over the generated profile: what it
    sets is taken as given, by `describe` as by `report`.
*   **Workspace** - the directory of samples and intermediate results; it may hold sensitive
    values, and keeps itself out of version control.

## How it works

1.  `scan` connects to the database given by its URL, the password taken from `.env`, and selects
    the tables by a list or a regular expression. For each table it counts the statistics of all
    columns in one query, the approximate distinct counts included; it counts the values of every
    column whose distinct count is below the enum threshold; and it takes a sample into the
    workspace. The detectors check the values of the sample; the semantic types they find are
    verified on the whole table where the detector has a pattern in SQL. The result is the
    profile.
2.  `describe` splits the original names of all columns into terms, and asks the language model
    for the word of each term, showing it the columns the term appears in. From the glossary and
    from each column's statistics, matches and sample, it asks for the column's name and
    description. Overrides are taken as given. The result is the profile, with glossary and
    suggestions.
3.  `report` renders the profile, with the overrides laid over it, as HTML.

## Principles

The design repeats a few decisions; new code follows them.

*   **The profile holds no sensitive values.** Raw values - the values of an enum, the range of a
    column - go into the profile only for columns of no sensitivity, and the range of texts never;
    samples stay in the workspace. A profile can be shared; a workspace cannot.
*   **No value leaves the machine.** The language model runs locally; no external service gets a
    value, a sample or a profile.
*   **The database is only read.** The tool sends nothing but queries.
*   **The dialect writes all SQL.** No other part writes SQL text, so that another database is a
    new dialect, not a change across the code.
*   **Detectors decide, the language model names.** What a column is, is found by deterministic
    detectors that can be tested; the language model proposes names and descriptions from what
    they found, and nothing else.
*   **One word per term.** Harmonized names are composed from the glossary, so that the same term
    reads the same in every table.
*   **The stages share nothing but the profile and the workspace.** Each stage can be run again on
    its own: `describe` with another model without querying the database, `report` without
    either.

## The repository

*   **`src/`** - the package `data_profiler`.
*   **`simulation/`** - the project `simulation`, with its package in `simulation/src/`.
*   **`docs/`** - the documents of the project: this one, the
    [coding guidelines](CODING-GUIDELINES.md) and one document per subject that outgrew its section
    here (see the list below).
*   **`issues/`** - the issues, one file each, and the overviews generated from them (see
    [issues/README.md](../issues/README.md)).
*   **`scripts/`** - the tools that check the rules of the documents, such as
    `scripts/wrapping.sh`.
*   **`.githooks/`** - the pre-commit hook, which runs the checks of the coding guidelines and keeps
    the issue overviews up to date; enabled per clone with `git config core.hooksPath .githooks`.
*   **`.claude/agents/`** - the agents Claude Code is given for the workflow of
    [AGENTS.md](../AGENTS.md#workflow), such as the `reviewer`.
*   **`AGENTS.md`** - how we work together; `CLAUDE.md` points Claude Code to it, and the links
    `.cursorrules` and `.clinerules` point Cursor and Cline to it.

## Documents

*   [CODING-GUIDELINES.md](CODING-GUIDELINES.md) - coding style, error handling, logging, tests,
    and the checks that run before every commit.
