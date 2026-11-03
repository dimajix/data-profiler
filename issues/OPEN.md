# Open Issues

The issues that are `open` or `in progress`: the bugs first, then by area, those of priority
`low` last; within a section by priority, then by number. Generated from the field lines of the
issue files by `issues/generate.sh`, like [INDEX.md](INDEX.md) - never edit it by hand.

## Bugs

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | low | bug | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |

## Profile

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [11](11-overrides.md) | in progress | medium | feature | A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe. Part of epic [02](02-first-version-epic.md). |

## Scan

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [23](23-sentinel-values.md) | open | medium | feature | A value that stands for no value - an empty text, `00000`, `9999-12-31` - is counted as a value like any other, so that a column of them looks filled, its range runs to the sentinel, and its share of a semantic type falls below the threshold. |

## Describe

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | in progress | high | question | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. Part of epic [02](02-first-version-epic.md). |
| [10](10-the-stage-describe.md) | open | high | feature | Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked. Part of epic [02](02-first-version-epic.md). |
| [24](24-terms-written-together.md) | open | medium | feature | Terms written together without a separator, `LFADR` in `KD_LFADR_PLZ`, stay one term, so that the glossary needs a word for every combination of terms, and the same term reads differently where it is written together. |

## Architecture

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [02](02-first-version-epic.md) | open | high | epic | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |

## Tooling and process

| No. | Status | Priority | Type | Issue |
|---|---|---|---|---|
| [14](14-a-dev-container.md) | in progress | high | feature | The tool cannot be run on the machine that reaches the real database in a prepared environment: it has to be set up there by hand, on Windows, with its proxy, its certificates and a local language model. |
