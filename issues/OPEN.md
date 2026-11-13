# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Bugs

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | low | bug | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |

## Scan

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [63](63-a-separator-of-lists-given-of-a-column.md) | open | medium | feature | The separator of lists is given of the project and of a table alone, so that the columns of a table whose lists are of different separators cannot all be found, and a column the tool takes wrongly for one of lists, or misses, cannot be corrected by an override of the column, nor a table of no lists be given none where the project gives one. |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [38](38-a-data-model-derived-from-the-profile-epic.md) | open | high | epic | The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them. |
