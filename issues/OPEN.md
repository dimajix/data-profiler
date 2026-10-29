# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Profile

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [03](03-the-profile.md) | open | high | feature | There is no profile yet: the stages have no format in which to hand on what they found about a database. Part of epic [02](02-first-version-epic.md). |

## Scan

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [06](06-source-and-dialect-for-trino.md) | open | high | feature | The tool cannot reach a database: nothing connects to Trino, lists its tables or sends it a query. Part of epic [02](02-first-version-epic.md). |

## Describe

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | open | high | question | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. Part of epic [02](02-first-version-epic.md). |

## Simulation

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [05](05-the-simulation-environment.md) | open | high | feature | There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed. Part of epic [02](02-first-version-epic.md). |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [02](02-first-version-epic.md) | open | high | epic | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |
