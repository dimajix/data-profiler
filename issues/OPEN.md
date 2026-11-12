# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Bugs

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | low | bug | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |
| [59](59-sentinels-given-that-a-type-cannot-hold.md) | open | low | bug | A sentinel given of a column that its type cannot hold - `N/A` of a `bigint`, `-1` of a `double`, which Trino writes `-1.0E0` - is left aside without a word, while sentinels given of a column of no text are refused, although both are overrides that cannot be what they give. |
| [60](60-the-range-of-times-in-the-contract-is-not-widened-to-their-sentinels.md) | open | low | bug | The data contract widens the range of a column to the sentinels found in it, which the range is counted without, but not that of a column of the logical type `time`, so that its rule of minimum and maximum fails on rows it was observed of. |

## Describe

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | in progress | high | question | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. Part of epic [02](02-first-version-epic.md). |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [02](02-first-version-epic.md) | open | high | epic | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |
| [38](38-a-data-model-derived-from-the-profile-epic.md) | open | high | epic | The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them. |

## Tooling and process

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [14](14-a-dev-container.md) | in progress | high | feature | The tool cannot be run on the machine that reaches the real database in a prepared environment: it has to be set up there by hand, on Windows, with its proxy, its certificates and a local language model. |

## Low priority

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [58](58-the-configuration-of-a-project-its-class-and-its-examples.md) | open | low | refactoring | The example project, the README and PROJECT.md show the configuration of a project otherwise than it is - without the semantic types, the separator of lists or the contract, and of an older format -, and which sentinels a column of a type can hold is decided in two places apart from the dialect, which knows the types. |
