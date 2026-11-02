# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Profile

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [11](11-overrides.md) | in progress | medium | feature | A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe. Part of epic [02](02-first-version-epic.md). |

## Detection

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [15](15-a-detector-of-uuids.md) | open | medium | feature | Nothing recognises a column of UUIDs written as text, so that a key of that kind is told to the language model as nothing but a text. |
| [16](16-semantic-types-of-a-project.md) | open | medium | feature | The semantic types are fixed in the code, so that a pattern of one database alone - an account number `A` and ten digits - cannot be recognised without changing the tool. |

## Describe

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | in progress | high | question | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. Part of epic [02](02-first-version-epic.md). |
| [10](10-the-stage-describe.md) | open | high | feature | Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked. Part of epic [02](02-first-version-epic.md). |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [02](02-first-version-epic.md) | open | high | epic | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |

## Tooling and process

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [14](14-a-dev-container.md) | in progress | high | feature | The tool cannot be run on the machine that reaches the real database in a prepared environment: it has to be set up there by hand, on Windows, with its proxy, its certificates and a local language model. |
