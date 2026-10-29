# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Profile

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [11](11-overrides.md) | open | medium | feature | A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe. Part of epic [02](02-first-version-epic.md). |

## Scan

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [06](06-source-and-dialect-for-trino.md) | open | high | feature | The tool cannot reach a database: nothing connects to Trino, lists its tables or sends it a query. Part of epic [02](02-first-version-epic.md). |
| [07](07-the-stage-scan.md) | open | high | feature | Nothing counts what the columns of a table hold - their nulls, their distinct values, their ranges, whether they are enums - and nothing takes a sample of them. Part of epic [02](02-first-version-epic.md). |

## Detection

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [08](08-detection.md) | open | high | feature | Nothing recognises what the values of a column are - phone numbers, postal codes, IBANs, card numbers, dates -, nor whether they are sensitive. Part of epic [02](02-first-version-epic.md). |

## Describe

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | open | high | question | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. Part of epic [02](02-first-version-epic.md). |
| [10](10-the-stage-describe.md) | open | high | feature | Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked. Part of epic [02](02-first-version-epic.md). |
| [09](09-the-glossary.md) | open | medium | feature | The original names are not split into their terms, so nothing can give a term one word for the whole database and compose harmonized names from it. Part of epic [02](02-first-version-epic.md). |

## Report

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [12](12-the-stage-report.md) | open | medium | feature | What the tool found can only be read as YAML: there is no report a person reads. Part of epic [02](02-first-version-epic.md). |

## Simulation

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [05](05-the-simulation-environment.md) | in progress | high | feature | There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed. Part of epic [02](02-first-version-epic.md). |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [02](02-first-version-epic.md) | open | high | epic | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |
