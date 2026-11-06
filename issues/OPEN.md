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
| [43](43-columns-of-lists-of-values.md) | open | medium | feature | A column whose texts are lists of values, separated by semicolons - `12;47;3` -, is taken for a column of texts like any other, so that what its values are, whether they are values of a key of another table, and whether they tell kinds of rows apart is not found: each text is counted whole, as a value of its own. |

## Detection

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [42](42-detectors-of-countries.md) | open | medium | feature | Nothing recognises a column of countries - written as a code of ISO 3166-1 of two letters, `DE`, or of three, `DEU`, as its number, `276`, or by its name, `Germany` -, so that a country is told to the language model as nothing but a text or a number. |

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
