# Architecture of data-profiler

This document draws the overall picture of the project - what the parts are, how they work
together, and the principles the design follows. Every section ends with the document that holds
the details, where there is one; the list at the end names them all.

data-profiler is a command line tool for data engineers that profiles the tables of an SQL
database - Trino and Starburst first - to help build an understandable data model of it: what each
column contains, and a harmonized name for it, composed from one glossary for the whole schema. It
reads the database through generated SQL, recognises the semantic types of columns with
deterministic detectors, and asks a small local language model for the concepts of the terms of
the names and for descriptions of the columns; no value leaves the machine it runs on.

The project is at its beginning: the parts below are the design it is built to, and come into the
code one by one.

## Parts

The tool is one Python package, `data_profiler`, in `src/`. The test data generator is a project of
its own, `simulation`, in `simulation/`: it uses the tool's profile and its detectors, but the tool
does not depend on it, nor on what it needs. Both are one uv workspace, with one lock file and one
environment.

*   **`data_profiler.profile`** - the profile: its classes and the version of their format, read
    and written as a directory of documents, one of the schema and one of each table; the profile
    a scan starts from, in its run, resumed or new; and the form the semantic types of a project
    take in a document, which `project` reads them in as well.
*   **`data_profiler.overrides`** - the overrides of a project: read as a document, and laid over
    each table a scan counts and over a profile a stage reads, refused where they name what is not
    profiled, give sentinels of a column of no text, or a reading of a name that is no reading of
    its terms, and warned of where they give an abbreviation no name has.
*   **`data_profiler.workspace`** - the workspace: the local directory of samples and intermediate
    results, which never leaves the machine; the samples and the enumerations of tables as
    Parquet.
*   **`data_profiler.project`** - the project: its configuration `project.yml` - the tables to
    profile, the semantic types of its own, the language model, and the environments, each by its
    URL, its user and its password, the password given by a variable -, its variables in `.env`,
    which complete those of the process, its overrides in `overrides.yml`, and the directories of
    the results of each environment.
*   **`data_profiler.documents`** - documents: the YAML files a person reads and writes, those of
    the profile and the configuration of a project among them, each the fields of one class with
    the version of its format; what is wrong with one is named, field by field.
*   **`data_profiler.files`** - files written whole or not at all, for documents and the
    workspace, under names every system takes - the names of tables among them.
*   **`data_profiler.source`** - the database: the `Source`, which `connect` makes from a URL, and
    the `Dialect`, which writes every SQL statement the tool sends. A source lists the tables and
    columns of its schema - their metadata - through its dialect, and runs queries in that schema,
    so that another database brings only its connection and its SQL. Trino is reached by HTTPS as a
    user with a password, both given apart from the URL; certificates and proxies come from the
    variables of the process.
*   **`data_profiler.values`** - values of the database, as the tool takes them: a count as a
    number, any value as text, as the profile holds it.
*   **`data_profiler.statistics`** - the statistics of a table, counted by one query that it builds
    from the building blocks of the dialect, and whose row it reads back.
*   **`data_profiler.enumerations`** - the enumerations of a table, their values counted by one
    query built the same way.
*   **`data_profiler.matching`** - the matches of a table: the semantic types of its columns,
    recognised in its sample by `detect`, and verified on the whole table by one query built the
    same way.
*   **`data_profiler.grouping`** - the groups of a table: its columns filled together, found in its
    sample.
*   **`data_profiler.disclosure`** - what of the values of a table goes into the profile: the
    ranges and the values of enumerations of its columns of no sensitivity, and the values of their
    samples shown to the language model, whose answers go into it.
*   **`data_profiler.sampling`** - the sample of a table, taken at random by a query built the same
    way.
*   **`data_profiler.scan`** - the stage `scan`: statistics, enumerations, samples, detector
    matches and groups of the selected tables, written to the profile table by table.
*   **`data_profiler.detect`** - what the values of a column are - of which semantic type and
    sensitivity, or sentinels of no value -, and the detectors that recognise them.
*   **`data_profiler.glossary`** - splitting the original names of tables and columns into terms,
    those written together by the vocabulary of the profile, each with its candidates among the
    concepts of the glossary, which the profile holds, and composing harmonized names from the
    readings of the names.
*   **`data_profiler.llm`** - the language model: a prompt answered in the form of a JSON schema,
    by the `LanguageModel`; `Ollama` runs one locally, reached past every proxy.
*   **`data_profiler.describe`** - the stage `describe`: the names of the tables and columns split
    into their terms, by a step of its own without the language model, and read - by the one
    candidate of each term, else by the language model -; and the glossary's concepts and the
    columns' descriptions, proposed by the language model.
*   **`data_profiler.report`** - the stage `report`: the profile rendered as one HTML document,
    its styles inside and no script, from a Jinja2 template in `data_profiler/templates/`.
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
`sampling`, `matching`, `grouping`, `overrides`, `disclosure`, `values` and `workspace`, `describe`
uses `glossary`, `overrides`, `llm`, `disclosure`, `values` and `workspace`, `report` the profile
and `overrides`, which it lays over it, and `glossary` for its names; `cli` runs the stages, gives
the overrides to each, and the language model, made by `llm` as the project names it, to `describe`,
unless it is to ask none. The semantic types of a project reach `scan` from `project`, and every
stage after it from the profile.

## The domain

*   **Project** - one database, profiled in environments: a directory of its configuration, which
    selects the tables, of its variables, which hold the passwords - and the users, where they
    differ from one person to the next - and are not shared, of its overrides, and of the results
    of each environment.
*   **Environment** - one of the places the database of a project is found - dev, test, prod, or
    the simulation environment -, each a schema with a URL, a user and a password of its own; its
    results, a profile, a workspace and a report, are kept in a directory of its own, named after
    it.
*   **Stage** - one of `scan`, `describe` and `report`: a step of the work that can be run on its
    own, from what the stages before it left.
*   **Run** - the counting of the selected tables of an environment, which may take several
    scans: a scan begins it, the next resumes it where it did not finish - failing at a table, or
    interrupted -, and it finishes once every selected table is counted. It is told apart by when
    it started, which each table it counted names.
*   **Source** - a schema of the database the tool reads, by its URL; **Dialect** - the SQL of
    one kind of database.
*   **Profile** - the documents describing the tables of one schema of a database: its tables and
    columns, what was found about them, the glossary, and the semantic types of its project; a
    directory of a document of the schema and a document of each table, so that a person reads a
    table in a file of its own. It is the only thing the stages hand to each other besides the
    workspace, and it holds no values of the columns found sensitive (see
    [Principles](#principles)).
*   **Table** and **Column** - as found in the database, under their original names.
*   **Statistics** - what is counted of a column on the whole table: its nulls, each of its
    sentinels, the approximate number of its distinct values, the range of its values, the range
    of lengths of texts, the last three without the sentinels. The rows are counted once per table.
*   **Sentinel** - a value that stands for no value: an empty text, `NULL`, `N/A`, `-`, a day such
    as `9999-12-31`. It is of no semantic type, and left aside as a null is, but each is counted
    apart and named in the profile with its rows, whatever the sensitivity of its column, so that
    a person can check them: the sentinels of the tool are fixed texts, and those given are of the
    overrides. The tool brings its sentinels, of the columns whose values the database writes as
    text; an override gives those of a column in their place.
*   **Enumeration** - a column with few distinct values, at most a threshold, of which not each is
    in one row alone; its values with the rows of each, its nulls and sentinels aside.
*   **Sample** - rows taken from a table at random, kept in the workspace.
*   **Semantic type** - what the values of a column are: a phone number, an IBAN, a date. Each has
    a **sensitivity**: personal data (GDPR), payment card data (PCI), or none. The tool brings its
    types; a project gives types of its own, each by a pattern alone, which the profile holds, so
    that it is read without its project.
*   **Detector** - recognises one semantic type: by a pattern every value of the type matches - in
    the values of a sample, and on the whole table in SQL -, by a check of a value where the
    pattern does not say enough, such as a checksum, and by a condition of the column where no
    value says enough alone, judged on the values of a sample together. Its type is a match of a
    column where it recognises at least its threshold of the values of the sample.
*   **Match** - a semantic type found in a column, with the share of values that match it in the
    sample and, once verified, in the whole table.
*   **Group** - columns of a table filled together, such as the street, the postal code and the
    city of a delivery address: in mostly the same rows of its sample, a column filled in a row
    where it holds a value, neither null nor a sentinel. Found by the Jaccard index of the rows
    each two columns are filled in, it holds its columns and its coherence, and a column does not
    name its group. A column filled in nearly every row, or in too few of the sample to be judged,
    is in none.
*   **Term** - a part of the original names, mostly an abbreviation: `CUST` in `CUST_CRT_DT`. The
    profile holds the terms of each name, as `describe` split it, each with the concepts written as
    it, its candidates, as the glossary had them then.
*   **Reading** - the concept each term of a name stands for, one word for each term at its place:
    `ap_ap_nm` read as AirPlus, contact person and name. `describe` reads a name whose terms have
    one candidate each, and keeps a reading while the terms of its name stay as they were split,
    their candidates among them; which concept a term of several stands for, the language model
    chooses, or an override gives. The terms and the reading of a name are written together, so that
    a profile never holds a reading of other terms than its own. A harmonized name is composed from
    the reading alone, unless an override gives the name.
*   **Vocabulary** - the terms a term written together is split into: those found in the names of
    a profile, and the terms its concepts are written as. A term is split only where other terms of
    the vocabulary cover it whole - `lfadr` in `KD_LFADR_PLZ` into `lf` and `adr` -, and a term a
    concept is written as never.
*   **Concept** - an entry of the glossary: a word, from which harmonized names are composed, the
    terms it is written as - its word, where the word is one term, and its abbreviations:
    `customer`, `cust` and `kd` for `customer` -, and its description, in English, from which the
    language model proposes descriptions of columns. A concept omitted is left out of the harmonized
    names, as a prefix that marks a custom column.
*   **Glossary** - the concepts of a profile, once for the whole profile, each under its word.
*   **Description** - what a column holds, in English, for a person who knows the business but not
    the database, proposed by the language model from the reading of its name, its statistics, its
    matches and its sample; its name is the harmonized one.
*   **Override** - what is given by hand of the profiles of a project, in its `overrides.yml`, and
    laid over a generated profile: concepts of the glossary, the reading of a name, the harmonized
    name of a table or column, the description of a column, and the sensitivity and the sentinels of
    a column. What it gives is taken as given by every stage: by `scan`, which counts the columns
    with their sentinels and marks them, by `describe`, which splits and reads the names by the
    concepts given and asks the language model for nothing given, as by `report`, which lays the
    concepts, readings, names, descriptions and marks over the profile; sentinels changed count once
    `scan` counts the column again, and a reading given once `describe` has split its name. A name
    given comes before the one composed from the reading, so that it resolves a collision of
    harmonized names. A concept given takes the place of the one proposed of its word, keeping of it
    the abbreviations proposed beside those given, and the terms it is written as are taken from the
    abbreviations of the others; the word of another stays a term of it, so that a term given may
    stand for either, as the reading of its name says.
*   **Workspace** - the directory of samples and intermediate results; it may hold sensitive
    values, and keeps itself out of version control.

## How it works

1.  `scan` connects to the schema of an environment of a project as its user, the password taken
    from a variable, and selects the tables the project names, by a list or a regular expression.
    For each table it counts the statistics of all columns in one query, the approximate distinct
    counts included, the sentinels of each column counted apart and left aside; it counts the values
    of every column whose distinct count is at most the threshold of an enumeration; and it takes a
    sample into the workspace. The detectors check the values of the sample, its sentinels aside;
    the semantic types they find are verified on the whole table by the patterns of the detectors in
    SQL. The columns filled together in the sample are named as groups. The overrides of the project
    give the sentinels of a column in place of those of the tool, and mark the columns the detectors
    miss. The result is the profile, with the ranges and the values of enumerations of the columns
    of no sensitivity, written after every table: a scan that fails keeps the tables before it, and
    the next scan resumes its run, skipping the tables it counted, unless the overrides now give
    their columns otherwise. It updates the profile there is: the tables no longer selected are
    dropped, the others kept until they are counted anew, and what the other stages filled is kept -
    the glossary, the terms and readings of the names that stay, and the descriptions of the
    columns; a profile scanned with other semantic types keeps its tables without their matches,
    values and ranges, until they are counted anew. A profile that cannot be read, or one of another
    schema, is refused and never overwritten: it may be the work of hours.
2.  `describe` splits the original names of all tables and columns into terms, those written
    together by the vocabulary, each with its candidates. It asks the language model of the project
    for the concept of each term of none, showing it the tables and columns the term appears in,
    with the values of their samples of no sensitivity, and proposes it into the glossary, a word
    there is taking the term as one more abbreviation. It splits the names again, reads each name
    whose terms have one candidate each, and asks the language model for the reading of each name of
    a term of several concepts, shown the concepts with their descriptions. From the reading of its
    name and the descriptions of its concepts, and from each column's statistics, matches, values,
    sample and the columns filled together with it, it asks for the column's description - its name
    stays the one harmonized. Overrides are taken as given: no term of a concept given, no name of a
    reading given and no column of a description given is asked for. The language model is asked
    only for what the profile lacks, and the profile is written after each concept and each table
    read or described, so that a run interrupted is resumed; `describe --anew` drops first what the
    language model filled, and `describe --without-llm` asks it nothing, doing what needs no model
    alone: the names split, and read where each term has one candidate. The result is the profile,
    with terms, glossary, readings and descriptions.
3.  `report` renders the profile, with the overrides laid over it, as HTML: the harmonized names and
    descriptions of the columns, and the concepts proposed told apart from those given.

## Principles

The design repeats a few decisions; new code follows them.

*   **The profile holds no values of the columns found sensitive.** Raw values - the values of an
    enumeration, the range of a column - go into the profile only for columns of no sensitivity;
    samples stay in the workspace. A profile can be shared; a workspace cannot. Sensitivity is
    judged optimistically: a column is sensitive where a sensitive type is one of its matches, or
    where an override marks it so - the mark comes first, and marks what the detectors miss -;
    each value that goes into the profile is checked on its own all the same, and withheld where it
    is of a sensitive type. The sentinels of a column are no values of it, and go into the profile
    whatever its sensitivity: those of the tool are fixed texts, those given are of the overrides.
*   **No value leaves the machine.** The language model runs locally, and is reached past every
    proxy, as its prompts hold values of samples; no external service gets a value, a sample or a
    profile.
*   **The database is only read.** The tool sends nothing but queries; only the simulation
    writes, into its own environment.
*   **The dialect writes all SQL.** No other part of the tool writes SQL text, so that another
    database is a new dialect, not a change across the code. What the tables hold is counted or
    sampled by queries that the part that reads their rows builds from the building blocks of the
    dialect: metadata belongs to the source, counting and sampling to the parts that do them.
*   **Every attribute of the profile is filled by one step.** A step, `scan` or a step of
    `describe`, replaces in a profile there is the attributes it fills alone, and keeps all others,
    so that a stage run again loses nothing another found: a scan keeps the terms and readings of
    the names and the descriptions of the columns, and splitting the names again keeps a reading
    while its terms stay. Which step fills which attribute is said once, in the module docs of
    `data_profiler.profile`.
*   **Detectors decide, the language model names.** What a column is, is found by deterministic
    detectors that can be tested; the language model proposes the concepts of terms and the
    descriptions of columns from what they found, and nothing else. It is shown the values of a
    sample as far as the profile may hold them - none of the columns of a sensitivity, none of a
    sensitive type -, as what it answers goes into the profile; where it needs more, the overrides
    give it.
*   **One word per concept.** Harmonized names are composed from the words of the concepts of the
    glossary, through the reading of each name, so that the same concept reads the same in every
    table, under whichever of its terms it is written; a name of no reading has none. Where
    two columns of a table come to the same name, the report shows it, rather than one name taking
    the place of the other. An override gives a name in place of the composed one, which resolves a
    collision.
*   **The stages share nothing but the profile and the workspace.** Each stage can be run again on
    its own: `describe` with another model without querying the database, `report` without
    either.

## The repository

*   **`src/`** - the package `data_profiler`; **`tests/`** - its tests.
*   **`work/`** - scripts of trials, such as that of issue 04: not a part of the tool, run by hand,
    checked as its code is; what holds is built into the tool by an issue of its own.
*   **`examples/`** - example projects of the tool, such as `examples/crm/`, which profiles the
    simulation environment.
*   **`projects/`** - the projects profiled with the tool, in a repository of their own, cloned or
    made there apart from this one, which ignores it; it does not depend on this one, and lies here
    so that the dev container reaches it. That repository keeps its projects with the results of
    their environments, the work done; it ignores their `.env`, and their workspaces keep
    themselves out of version control.
*   **`simulation/`** - the project `simulation`, with its package in `simulation/src/`, its tests
    in `simulation/tests/`, an example profile in `simulation/profiles/`, and in
    `simulation/trino/` the configuration of the simulated Trino.
*   **`docker-compose.yml`** - the simulation environment, started as `README.md` says.
*   **`.devcontainer/`** - the dev container of Visual Studio Code, with Ollama beside it, for the
    machine that reaches the real database; the certificates of the company go into its `certs/`,
    which keeps them out of version control.
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
