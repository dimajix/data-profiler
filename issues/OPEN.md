# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Bugs

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | low | bug | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |

## Export

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [67](67-the-sentinels-of-the-tool-in-the-contract.md) | open | medium | feature | The data contract writes, of every column of no nulls and no sentinels found, a rule against all the sentinels of the tool its type can hold - `''`, `NULL`, `null`, `N/A`, `n/a`, `-` of every column of text, the six forms of the first and the last day of every date -, although neither the overrides nor the data name them, so that the contract is full of sentinels nobody gave and nothing holds. |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [38](38-a-data-model-derived-from-the-profile-epic.md) | open | high | epic | The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them. |
