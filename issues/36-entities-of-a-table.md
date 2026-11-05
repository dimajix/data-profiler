# 36 — Entities of a table

**Status:** open
**Type:** feature
**Priority:** high
**Area:** Scan
**Epic:** [38](38-a-data-model-derived-from-the-profile-epic.md)
**Summary:** A table that holds the rows of several entities of the business - told apart by a simple condition, such as the value of a column of their kind, each with columns of its own filled - is profiled as one, so that nothing tells which entities it holds and which columns belong to each.

## The problem

One table of the CRM holds the rows of four or five entities the business tells apart. Each is
told apart from the others by a simple condition, mostly the value of one column, and each has
columns of its own filled, which the rows of the others leave empty. The profile counts, samples
and describes the table as one: the nulls of a column are a mean over the entities, the groups
([25](25-groups-of-columns-filled-together.md)) mix the columns of several, and nothing says which
entities there are, by which condition, and which columns are of which.

## Why it matters

A data model that fits the processes of the business holds each of these entities as one of its
own ([38](38-a-data-model-derived-from-the-profile-epic.md)). It is a split of the rows, not a
normalization ([37](37-values-determined-by-another-column.md)): every row stays whole, in the
entity it belongs to, and the condition is what selects the rows of the entity from the table in
the database - the `WHERE` of a view that maps the model onto it.

## What is to be decided

The interface first, put before the maintainer.

- **The name of the concept.** What is found is the rows of a table of one kind, told apart by a
  condition. Proposed: *entity*, `Table.entities`, as it is what the model holds; *type* is the
  semantic type already. Whether a table of one entity names it, or names none.
- **The condition.** Proposed for the first version: one column, the *discriminator*, and the
  values that select the rows of each entity (`kind IN ('K', 'L')`) - the column an enumeration,
  whose values `scan` counts on the whole table already. Whether the condition may be more: a
  column null or filled, two columns together. The condition is held as a structure, not as SQL:
  the dialect writes all SQL, and the overrides hold none.
- **How the discriminator is found.** Two ways:
  - *From the columns.* Each enumeration is a candidate; for each of its values, the share of its
    rows of the sample each column is filled in, as `detect.is_filled` says. A discriminator
    separates: within the rows of one value, a column is filled in nearly all or nearly none, and
    which are filled differs between the values. Measured by how much the values of the candidate
    tell of whether the columns are filled - the information gain, summed over the columns -, the
    best candidate taken above a threshold. Values whose rows fill the same columns are one entity:
    joined by clustering, as the columns of a group are.
  - *From the rows.* The rows of the sample clustered by the columns they fill, and the condition
    that tells the clusters apart sought afterwards. It finds entities no column tells apart, but
    the condition then is complex or none.

  Proposed: from the columns, as the conditions of the case are simple; from the rows later, where
  that finds none and someone needs it.
- **Verified on the whole table.** A value of few rows may be missing from the sample. One query
  grouped by the discriminator counts the rows of each value and the rows each column is filled in,
  built from the building blocks of the dialect, as the enumerations are: the shares of each entity
  exact, not of the sample.
- **The columns of an entity.** Each column with the share of the rows of each entity it is filled
  in: those filled in every entity are of all, the others of the entities that fill them. Whether
  the profile holds the shares, or the columns of each entity by a threshold.
- **What the profile holds.** In the document of the table, its discriminator and its entities,
  each with its values, its rows and its columns; the format raised by its minor part, as
  [33](33-major-and-minor-versions-of-the-formats.md) says of fields added.
- **What the overrides give.** The discriminator of a table, its entities with their values -
  joined or split as the business tells them apart -, and the name and description of each; a
  table of no entities where some are found. Whether the language model proposes a name and a
  description of an entity from the readings of its columns, in `describe`.
- **What follows from it.** The statistics, matches and groups of the columns of an entity, counted
  within its rows, say more than over the table: a column of an entity filled in all its rows is
  not one of 80 % nulls. Whether `scan` counts them per entity, by one query grouped by the
  discriminator, or that is left to an issue of its own. The keys ([34](34-primary-keys.md)) and
  the references ([35](35-references-between-tables.md)) of an entity follow from it.
- **The report** shows the entities of a table as a matrix of its columns and its entities, each
  cell the share of the rows filled, so that a person checks the split at a glance.

## Done when

- The interface is agreed with the maintainer.
- `scan` finds the entities of a table by their discriminator and its values, with the columns of
  each, verified on the whole table.
- The overrides give the discriminator, the entities and their names.
- The report shows the entities; the simulation generates a table of several entities - a column
  of their kind, and columns filled by kind -, which a test finds.

## History

- **2026-11-05** — Opened with [38](38-a-data-model-derived-from-the-profile-epic.md), as agreed
  with the maintainer: the table of four or five entities of the CRM is split by its rows, by a
  simple condition, not normalized.
