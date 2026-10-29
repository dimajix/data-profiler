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
| [11](11-overrides.md) | open | A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe. |

## Scan

| No. | Status | Issue |
|---|---|---|
| [06](06-source-and-dialect-for-trino.md) | open | The tool cannot reach a database: nothing connects to Trino, lists its tables or sends it a query. |
| [07](07-the-stage-scan.md) | open | Nothing counts what the columns of a table hold - their nulls, their distinct values, their ranges, whether they are enums - and nothing takes a sample of them. |

## Detection

| No. | Status | Issue |
|---|---|---|
| [08](08-detection.md) | open | Nothing recognises what the values of a column are - phone numbers, postal codes, IBANs, card numbers, dates -, nor whether they are sensitive. |

## Describe

| No. | Status | Issue |
|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | open | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. |
| [09](09-the-glossary.md) | open | The original names are not split into their terms, so nothing can give a term one word for the whole database and compose harmonized names from it. |
| [10](10-the-stage-describe.md) | open | Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked. |

## Report

| No. | Status | Issue |
|---|---|---|
| [12](12-the-stage-report.md) | open | What the tool found can only be read as YAML: there is no report a person reads. |

## Simulation

| No. | Status | Issue |
|---|---|---|
| [05](05-the-simulation-environment.md) | in progress | There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed. |

## Architecture

| No. | Status | Issue |
|---|---|---|
| [02](02-first-version-epic.md) | open | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |

## Tooling and process

| No. | Status | Issue |
|---|---|---|
| [01](01-initial-project-setup.md) | done | The repository is still the generic project template: its documents, checks and issue areas say nothing yet about this project, its language or its tools. |
