# 38 — A data model derived from the profile

**Status:** open
**Type:** epic
**Priority:** high
**Area:** Architecture
**Summary:** The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them.

## The problem

The profile is to serve a new data model of the CRM, one that fits its processes better than the
tables do. Some tables are only to be renamed - the harmonized names give that already -, others
hold several entities of the business and are to be split. What the model needs beyond the names,
the profile does not hold: the keys of the tables, the references between them, the entities a
table holds. And nothing takes the step from the profile to the model; a person does it by hand,
from the report.

## Why it matters

Deriving the model by hand from 20 tables of up to 200 columns is the work the tool is to take
off a person. What the tool finds, it finds from the data, deterministically, and shows with its
evidence - the share of rows that agree -, so that a person decides each step of the model by
checking it rather than by finding it.

## The order

Each issue finds one kind of what the model is made of, held by the profile, given or rejected by
the overrides and shown by the report:

- [36](36-entities-of-a-table.md) - the entities of a table, its rows split by a simple condition.
  It is what the model needs most and rests on none of the others, so it comes first.
- [34](34-primary-keys.md) - the keys of the tables.
- [35](35-references-between-tables.md) - the references between the tables, to their keys, and to
  the entities of a table, so that it comes after both.
- [37](37-values-determined-by-another-column.md) - the columns determined by another than the key,
  for a normalization; of lower priority, after the split.

Then the model itself, opened as issues once the findings above are there, as its shape rests on
them:

- **The model.** Its entities - a table renamed, or an entity of a table -, their attributes, keys
  and references, derived from the profile and the overrides, each attribute naming the column it
  comes from. To be decided: a stage of its own, `model`, and a document of the model, which a
  person edits - whether it belongs to the project, as the overrides do, or to the results of an
  environment, as the profile does; the overrides of the model - an entity renamed, joined,
  rejected -; and whether the language model proposes the names and descriptions of entities.
- **The model shown.** The model in the report, with a diagram of its entities and references, as
  SVG rendered with the report, since the report holds no script.
- **The model mapped.** The model onto the database, as views of each entity from the table it
  comes from, its condition the `WHERE` of the view, written by the dialect: the way to check the
  model on the data before anything is migrated.

## Done when

- The issues above, and those of the model, are done.
- Against the simulation environment, the stages leave a model of its tables - the tables renamed,
  one split into its entities, with their keys and references -, which the report shows.

## History

- **2026-11-05** — Opened with [34](34-primary-keys.md), [35](35-references-between-tables.md),
  [36](36-entities-of-a-table.md) and [37](37-values-determined-by-another-column.md), as agreed
  with the maintainer: the model is to fit the processes of the business, which needs tables
  renamed and split by the entities they hold, a split of their rows by a simple condition, not a
  normalization.
