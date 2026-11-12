# 02 — First version: scan, describe and an HTML report

**Status:** done
**Type:** epic
**Priority:** high
**Area:** Architecture
**Summary:** The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found.

## The problem

[01](01-initial-project-setup.md) decided what data-profiler is and how it is built - its parts, its
domain and its principles are in `docs/ARCHITECTURE.md` -, but none of the parts exists. The first
case waits for it: a CRM of about 20 tables of up to 200 columns, behind abbreviated names, of which
a readable data model is to be made, without its data reaching an external language model.

## Why it matters

The first version is what the design is checked against: whether the stages can share nothing but
the profile and the workspace, whether a small local model names columns well enough, whether the
profile can be kept free of sensitive values. Each issue below either builds a part or answers one
of these questions, in the order in which the later ones rest on the earlier.

## The order

- [03](03-the-profile.md) - the profile, which every stage reads or writes; its interface comes
  first.
- [04](04-can-a-small-model-name-columns.md) - a trial by hand of whether a model of 1 to 2
  billion parameters names columns well from prepared facts. It is the largest risk of the design,
  and it costs no code, so it comes early; its answer shapes [10](10-the-stage-describe.md).
- [05](05-the-simulation-environment.md) - Trino, PostgreSQL and Ollama in Docker, and test data
  generated from a profile, since the real database is not reachable where the tool is developed.
- [06](06-source-and-dialect-for-trino.md) - the connection to Trino and the SQL it is sent.
- [07](07-the-stage-scan.md) - the stage `scan`: statistics, enumerations, samples, and with it the
  command line.
- [08](08-detection.md) - semantic types, their sensitivity, and the detectors.
- [09](09-the-glossary.md) - original names split into terms, and harmonized names composed from
  their words, without a language model.
- [27](27-glossary-of-concepts.md) - the glossary as concepts, each with its word, its
  abbreviations and its description, an abbreviation of several concepts by its meaning in a name,
  and concepts left out of the names.
- [24](24-terms-written-together.md) - terms written together split by the vocabulary of the
  schema, before or with the words of the glossary.
- [28](28-terms-and-readings.md) - the terms of each name with their concepts, and its reading of
  one concept each, held in the profile by steps of `describe` of their own, which `scan` keeps.
- [10](10-the-stage-describe.md) - the stage `describe`: the words of the terms and the names of
  the columns, proposed by the language model.
- [11](11-overrides.md) - corrections written by hand, laid over the profile.
- [12](12-the-stage-report.md) - the stage `report`: the profile as HTML.

Not in the first version: PDF, the relationships between tables, other databases than Trino.

## Done when

- The issues above are done.
- Against the simulation environment, `scan`, `describe` and `report` run one after another and
  leave a profile, which holds no sensitive values, and an HTML report of its tables.
- `README.md` says how the tool is run.

## History

- **2026-10-29** — Opened with the plan of the first version, agreed with the maintainer after
  [01](01-initial-project-setup.md).

- **2026-11-03** — [24](24-terms-written-together.md) added to the order, after
  [09](09-the-glossary.md), as the maintainer decided: terms written together are split before
  the language model is asked for their words.

- **2026-11-03** — [27](27-glossary-of-concepts.md) added to the order, before
  [24](24-terms-written-together.md), as the maintainer decided: the vocabulary that splits the
  terms written together are the abbreviations of the concepts of the glossary.

- **2026-11-03** — [28](28-terms-and-readings.md) added to the order, after
  [24](24-terms-written-together.md) and before [10](10-the-stage-describe.md), as the maintainer
  decided: the names are split and read by steps of `describe` without a language model, before
  it proposes names and descriptions.

- **2026-11-12** — The stage `report` is now the stage `export`, which writes the report into
  `export/html/` of the environment ([57](57-export-as-open-data-contract.md)); where this issue
  names `report`, the command is `export`.

- **2026-11-12** — Closed by the maintainer, as the last issue of the order,
  [04](04-can-a-small-model-name-columns.md), is done: `qwen3.5:2b` names the columns of the real
  database well enough. Done.
