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
| [61](61-enumerations-given-and-of-types-that-are-none.md) | in progress | medium | feature | Whether a column is an enumeration is decided by the count of its distinct values alone, so that a column of UUIDs, of dates, times or moments, or of floating numbers is taken for one where it has few values, and nothing can be given by hand to make a column an enumeration or none, where the tool decides otherwise. |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [38](38-a-data-model-derived-from-the-profile-epic.md) | open | high | epic | The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them. |
