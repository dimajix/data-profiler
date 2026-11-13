# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Bugs

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | low | bug | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |

## Detection

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [66](66-detectors-of-json-documents.md) | in progress | medium | feature | Nothing recognises a column of text whose values are JSON documents - objects or arrays, such as payloads, settings or attributes of a row -, nor the broken documents among them, so that such a column is told to the language model as nothing but a text, and is checked for codes, enumerations and free text like any other. |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [38](38-a-data-model-derived-from-the-profile-epic.md) | open | high | epic | The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them. |
