# Architecture of data-profiler

This document draws the overall picture of the project - what the parts are, how they work
together, and the principles the design follows. Every section ends with the document that holds
the details, where there is one; the list at the end names them all.

data-profiler is a command line tool for data engineers that profiles the tables of an SQL
database - Trino and Starburst first - to help build an understandable data model of it: what each
column contains, and a harmonized name for it, composed from one glossary for the whole schema. It
reads the database through generated SQL, recognises the semantic types of columns with
deterministic detectors, and asks a small local language model for names; no value leaves the
machine it runs on.

The project is at its beginning: the parts below are the design it is built to, and come into the
code one by one.

## Parts

The tool is one Python package, `data_profiler`, in `src/`. The test data generator is a project of
its own, `simulation`, in `simulation/`: it uses the tool's profile, but the tool does not depend on
it, nor on what it needs. Both are one uv workspace, with one lock file and one environment.

*   **`data_profiler.profile`** - the profile: its classes and the version of their format, read
    and written as a document, and laying overrides over it.
*   **`data_profiler.workspace`** - the workspace: the local directory of samples and intermediate
    results, which never leaves the machine; the samples and the enumerations of tables as
    Parquet.
*   **`data_profiler.project`** - the project: its configuration `project.yml` - the tables to
    profile, and the environments, each by its URL and its password, the password given by a
    variable -, its variables in `.env`, which complete those of the process, and the directories
    of the results of each environment.
*   **`data_profiler.documents`** - documents: the YAML files a person reads and writes, the profile
    and the configuration of a project among them, each the fields of one class with the version of
    its format; what is wrong with one is named, field by field.
*   **`data_profiler.files`** - files written whole or not at all, for documents and the
    workspace.
*   **`data_profiler.source`** - the database: the `Source`, which `connect` makes from a URL, and
    the `Dialect`, which writes every SQL statement the tool sends. A source lists the tables and
    columns of its schema - their metadata - through its dialect, and runs queries in that schema,
    so that another database brings only its connection and its SQL. Trino is reached by HTTPS with
    a password; certificates and proxies come from the variables of the process.
*   **`data_profiler.statistics`** - the statistics of a table, counted by one query that it builds
    from the building blocks of the dialect, and whose row it reads back.
*   **`data_profiler.enumerations`** - the enumerations of a table, their values counted by one
    query built the same way.
*   **`data_profiler.matching`** - the matches of a table: the semantic types of its columns,
    recognised in its sample by `detect`.
*   **`data_profiler.sampling`** - the sample of a table, taken at random by a query built the same
    way.
*   **`data_profiler.scan`** - the stage `scan`: statistics, enumerations, samples and detector
    matches of the selected tables, written to a profile.
*   **`data_profiler.detect`** - the semantic types, their sensitivity, and the detectors that
    recognise them.
*   **`data_profiler.glossary`** - splitting original names into terms, and composing harmonized
    names from the words of the glossary.
*   **`data_profiler.describe`** - the stage `describe`: the glossary's words and the columns'
    names and descriptions, proposed by the language model.
*   **`data_profiler.report`** - the stage `report`: the profile rendered as HTML.
*   **`data_profiler.cli`** - the command line: it reads the arguments, and runs the stages on an
    environment of a project through `commands`.
*   **`data_profiler.commands`** - the frame every command line of the project, the simulation's
    as well, runs its work in: it alone configures the log and ends the program, showing users
    what may be shown of an error.
*   **`simulation`** - test data: tables generated from a profile and loaded into the simulation
    environment - Trino, reached by HTTPS with a password as Starburst is, with a PostgreSQL
    catalog, and Ollama under a compose profile of its own -, for tests and for trying the tool
    without access to the real database. It creates the tables by Trino and fills them by `COPY` in
    the PostgreSQL behind the catalog, where Trino has named them in lower case.

The stages read and write the profile: `scan` uses `source`, `statistics`, `enumerations`,
`sampling`, `detect` and `workspace`, `describe` uses `glossary` and `workspace`, `report` the
profile alone; `cli` runs the stages.

## The domain

*   **Project** - one database, profiled in environments: a directory of its configuration, which
    selects the tables, of its variables, which hold the passwords and are not shared, and of the
    results of each environment.
*   **Environment** - one of the places the database of a project is found - dev, test, prod, or
    the simulation environment -, each a schema with a URL and a password of its own; its results,
    a profile and a workspace, are kept in a directory of its own, named after it.
*   **Stage** - one of `scan`, `describe` and `report`: a step of the work that can be run on its
    own, from what the stages before it left.
*   **Source** - a schema of the database the tool reads, by its URL; **Dialect** - the SQL of
    one kind of database.
*   **Profile** - the document describing the tables of one schema of a database: its tables and
    columns, what was found about them, and the glossary. It is the only thing the stages hand to
    each other besides the workspace, and it holds no sensitive values (see
    [Principles](#principles)).
*   **Table** and **Column** - as found in the database, under their original names.
*   **Statistics** - what is counted of a column on the whole table: its nulls, the approximate
    number of its distinct values, the range of numbers and dates, the range of lengths of texts.
    The rows are counted once per table.
*   **Enumeration** - a column with few distinct values, at most a threshold, of which not each is
    in one row alone; its values with the rows of each.
*   **Sample** - rows taken from a table at random, kept in the workspace.
*   **Semantic type** - what the values of a column are: a phone number, an IBAN, a date. Each has
    a **sensitivity**: personal data (GDPR), payment card data (PCI), or none.
*   **Detector** - recognises one semantic type: by a pattern every value of the type matches - in
    the values of a sample, and on the whole table in SQL -, and by a check of a value where the
    pattern does not say enough, such as a checksum.
*   **Match** - a semantic type found in a column, with the share of values that match it in the
    sample and, once verified, in the whole table.
*   **Term** - a part of the original names, mostly an abbreviation: `CUST` in `CUST_CRT_DT`.
*   **Glossary** - the word each term of a profile stands for, once for the whole profile:
    `customer` for `CUST`.
*   **Suggestion** - the harmonized name and the description proposed for a column, in English, the
    name composed from the words of the glossary.
*   **Override** - a part of a profile, written by hand, laid over the generated profile: what it
    sets is taken as given, by `describe` as by `report`.
*   **Workspace** - the directory of samples and intermediate results; it may hold sensitive
    values, and keeps itself out of version control.

## How it works

1.  `scan` connects to the schema of an environment of a project, the password taken from a
    variable, and selects the tables the project names, by a list or a regular expression. For each
    table it counts the statistics of all columns in one query, the approximate distinct counts
    included; it counts the values of every column whose distinct count is at most the threshold of
    an enumeration; and it takes a sample into the workspace. The detectors check the values of the
    sample; every semantic type one of them is of is verified on the whole table by the pattern of
    its detector in SQL. The result is the profile.
2.  `describe` splits the original names of all columns into terms, and asks the language model
    for the word of each term, showing it the columns the term appears in. From the glossary and
    from each column's statistics, matches and sample, it asks for the column's name and
    description. Overrides are taken as given. The result is the profile, with glossary and
    suggestions.
3.  `report` renders the profile, with the overrides laid over it, as HTML.

## Principles

The design repeats a few decisions; new code follows them.

*   **The profile holds no sensitive values.** Raw values - the values of an enumeration, the range
    of a column - go into the profile only for columns of no sensitivity, and the range of texts
    never; samples stay in the workspace. A profile can be shared; a workspace cannot.
*   **No value leaves the machine.** The language model runs locally; no external service gets a
    value, a sample or a profile.
*   **The database is only read.** The tool sends nothing but queries; only the simulation
    writes, into its own environment.
*   **The dialect writes all SQL.** No other part of the tool writes SQL text, so that another
    database is a new dialect, not a change across the code. What the tables hold is counted or
    sampled by queries that the part that reads their rows builds from the building blocks of the
    dialect: metadata belongs to the source, counting and sampling to the parts that do them.
*   **Detectors decide, the language model names.** What a column is, is found by deterministic
    detectors that can be tested; the language model proposes names and descriptions from what they
    found, and nothing else.
*   **One word per term.** Harmonized names are composed from the glossary, so that the same term
    reads the same in every table.
*   **The stages share nothing but the profile and the workspace.** Each stage can be run again on
    its own: `describe` with another model without querying the database, `report` without
    either.

## The repository

*   **`src/`** - the package `data_profiler`; **`tests/`** - its tests.
*   **`examples/`** - example projects of the tool, such as `examples/crm/`, which profiles the
    simulation environment.
*   **`simulation/`** - the project `simulation`, with its package in `simulation/src/`, its tests
    in `simulation/tests/`, an example profile in `simulation/profiles/`, and in
    `simulation/trino/` the configuration of the simulated Trino.
*   **`docker-compose.yml`** - the simulation environment, started as `README.md` says.
*   **`docs/`** - the documents of the project: this one, the
    [coding guidelines](CODING-GUIDELINES.md) and one document per subject that outgrew its section
    here (see the list below).
*   **`issues/`** - the issues, one file each, and the overviews generated from them, under areas
    that follow the parts above (see [issues/README.md](../issues/README.md)).
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
