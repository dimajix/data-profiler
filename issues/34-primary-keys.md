# 34 — Primary keys

**Status:** open
**Type:** feature
**Priority:** high
**Area:** Scan
**Epic:** [38](38-a-data-model-derived-from-the-profile-epic.md)
**Summary:** Nothing tells which columns identify the rows of a table, so that a data model derived from the profile has no keys, and no reference of another table can be found to them.

## The problem

The profile holds what each column contains, but not which of them identify a row. Trino names no
keys: its `information_schema` has no constraints, and the tables of the CRM have none declared.
What identifies a row is to be found in the data, as everything else in the profile is.

## Why it matters

A data model is made of entities with their keys, and of references between them. The references
([35](35-references-between-tables.md)) are found to the keys of the tables they point to: without
the keys, there is nothing to look for. A key is also what a person checks first of a table they do
not know.

## What is to be decided

The interface first, put before the maintainer.

- **The candidates of one column.** A column of no nulls and no sentinels, whose distinct values
  are about as many as the rows. The statistics count them already, but approximately - the
  distinct count of Trino errs by about 2 % -, so that they name candidates, not keys. Whether
  columns of floating point numbers, of free text and of timestamps are left out, which may be
  unique by chance.
- **Candidates of several columns.** The smallest combinations of two or three columns of no nulls
  whose values are unique in the sample - a history table of `(id, valid_from)`. Unique in the
  sample is necessary, not sufficient: in 10,000 rows of a table of millions many combinations are
  unique by chance. The pairs of 200 columns are 19,900, which the sample allows; triples only of
  columns of many distinct values.
- **Verified on the whole table.** By one query per table, counting the distinct values of each
  candidate exactly, built from the building blocks of the dialect, as the statistics are. What it
  costs on a table of hundreds of millions of rows; whether exact distinct counts of several
  columns together are a building block every dialect can give.
- **The primary key.** Among the keys verified, the one a person would take: of a reading of
  `identifier`, `number` or `key`, of an integer or a UUID, of the fewest columns, the first in the
  table. Whether the profile holds the keys and marks one as primary, or holds the primary alone.
- **What the profile holds.** In the document of the table, each key with its columns, and which is
  primary; the format raised by its minor part, as
  [33](33-major-and-minor-versions-of-the-formats.md) says of fields added.
- **What the overrides give.** The primary key of a table, by its columns, where the one chosen is
  not the one of the business, or where none was found. Whether a key given that the table does not
  hold unique is refused, warned of, or taken as given.
- **Where it is found.** By `scan`, table by table, after the statistics and the sample, so that a
  run resumed finds the keys of the tables it counts.
- **Keys of an entity.** In a table of several entities ([36](36-entities-of-a-table.md)), a
  column may be unique within the rows of one entity alone; whether that is found, or left to the
  overrides.
- **The report** shows the keys of each table.

## Done when

- The interface is agreed with the maintainer.
- `scan` finds the keys of a table of one column and of several, verified on the whole table, and
  names the primary key in the profile.
- The overrides give the primary key of a table.
- The report shows the keys; the simulation generates a table whose key is of two columns, which a
  test finds.

## History

- **2026-11-05** — Opened with [38](38-a-data-model-derived-from-the-profile-epic.md), as agreed
  with the maintainer: the keys are the first of what a data model derived from the profile needs.
