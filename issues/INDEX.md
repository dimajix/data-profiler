# Issues — Index

Every issue, one line each, under its area and by number. Generated from the field lines of the
issue files by `issues/generate.sh` - never edit it by hand: change the issue file, and the
pre-commit hook (`.githooks/pre-commit`) or a run of the script brings this file up to date. How
issues are kept is described in [README.md](README.md); those open or in progress are listed in
[OPEN.md](OPEN.md).

## Profile

| No. | Status | Issue |
|---|---|---|
| [03](03-the-profile.md) | done | There is no profile yet: the stages have no format in which to hand on what they found about a database. |
| [11](11-overrides.md) | in progress | A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe. |
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |

## Scan

| No. | Status | Issue |
|---|---|---|
| [06](06-source-and-dialect-for-trino.md) | done | The tool cannot reach a database: nothing connects to Trino, lists its tables or sends it a query. |
| [07](07-the-stage-scan.md) | done | Nothing counts what the columns of a table hold - their nulls, their distinct values, their ranges, whether they are enumerations - and nothing takes a sample of them. |
| [18](18-a-scan-written-table-by-table.md) | done | A scan writes its profile only once it has counted every table, so that a run that fails or is interrupted at one table loses all the tables before it, and a new scan replaces the profile whole. |

## Detection

| No. | Status | Issue |
|---|---|---|
| [08](08-detection.md) | done | Nothing recognises what the values of a column are - phone numbers, postal codes, IBANs, card numbers, dates -, nor whether they are sensitive. |
| [15](15-a-detector-of-uuids.md) | done | Nothing recognises a column of UUIDs written as text, so that a key of that kind is told to the language model as nothing but a text. |
| [16](16-semantic-types-of-a-project.md) | done | The semantic types are fixed in the code, so that a pattern of one database alone - an account number `A` and ten digits - cannot be recognised without changing the tool. |
| [20](20-detectors-of-boolean-pairs.md) | open | Nothing recognises a column of flags written as `true`/`false`, `yes`/`no` or `0`/`1`, so that a flag is told to the language model as nothing but a text or a number. |
| [21](21-a-detector-of-free-text.md) | open | Nothing recognises a column of free text - comments, notes, descriptions -, so that it is told to the language model as a text like any other, and its values are disclosed like those of a code. |

## Describe

| No. | Status | Issue |
|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | in progress | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. |
| [09](09-the-glossary.md) | done | The original names are not split into their terms, so nothing can give a term one word for the whole database and compose harmonized names from it. |
| [10](10-the-stage-describe.md) | open | Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked. |

## Report

| No. | Status | Issue |
|---|---|---|
| [12](12-the-stage-report.md) | done | What the tool found can only be read as YAML: there is no report a person reads. |

## Command line

| No. | Status | Issue |
|---|---|---|
| [13](13-projects-and-environments.md) | done | Nothing keeps the configuration of a database together with the results of profiling it, so every run is given the URL, the tables and the paths anew, and the same database in dev, test and prod cannot be profiled side by side. |
| [17](17-the-user-apart-from-the-url.md) | done | The user of an environment is part of its URL, so that it cannot be taken from a variable while the host, the catalog and the schema stay in the configuration the team shares. |

## Simulation

| No. | Status | Issue |
|---|---|---|
| [05](05-the-simulation-environment.md) | done | There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed. |

## Architecture

| No. | Status | Issue |
|---|---|---|
| [02](02-first-version-epic.md) | open | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |

## Tooling and process

| No. | Status | Issue |
|---|---|---|
| [01](01-initial-project-setup.md) | done | The repository is still the generic project template: its documents, checks and issue areas say nothing yet about this project, its language or its tools. |
| [14](14-a-dev-container.md) | in progress | The tool cannot be run on the machine that reaches the real database in a prepared environment: it has to be set up there by hand, on Windows, with its proxy, its certificates and a local language model. |
