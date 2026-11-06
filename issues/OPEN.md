# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Bugs

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | low | bug | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |

## Relate

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [35](35-references-between-tables.md) | in progress | high | feature | Nothing tells which columns of a table refer to the key of another - the customer of an order -, so that the relationships between the tables, which a data model is made of, are left to a person to find. Part of epic [38](38-a-data-model-derived-from-the-profile-epic.md). |

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
| [37](37-values-determined-by-another-column.md) | open | low | feature | Nothing tells which columns of a table are determined by another column than its key - the name of a customer repeated in each of its orders -, so that values copied from another entity, which a normalized model holds once, are not seen. Part of epic [38](38-a-data-model-derived-from-the-profile-epic.md). |
