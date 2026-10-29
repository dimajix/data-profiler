# Issues — Index

Every issue, one line each, under its area and by number. Generated from the field lines of the
issue files by `issues/generate.sh` - never edit it by hand: change the issue file, and the
pre-commit hook (`.githooks/pre-commit`) or a run of the script brings this file up to date. How
issues are kept is described in [README.md](README.md); those open or in progress are listed in
[OPEN.md](OPEN.md).

## Profile

| No. | Status | Issue |
|---|---|---|
| [03](03-the-profile.md) | open | There is no profile yet: the stages have no format in which to hand on what they found about a database. |

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

## Simulation

| No. | Status | Issue |
|---|---|---|
| [05](05-the-simulation-environment.md) | open | There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed. |

## Architecture

| No. | Status | Issue |
|---|---|---|
| [02](02-first-version-epic.md) | open | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |

## Tooling and process

| No. | Status | Issue |
|---|---|---|
| [01](01-initial-project-setup.md) | done | The repository is still the generic project template: its documents, checks and issue areas say nothing yet about this project, its language or its tools. |
