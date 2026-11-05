# 34 — Primary keys

**Status:** in progress
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

## How

As decided with the maintainer, in two steps - the keys found, then the primary key given:

- **The concepts:** a *key* is a set of columns whose values identify each row, verified on the
  whole table, and minimal; `Table.keys` holds those of one column and of two, the fewer columns
  first, and `Table.primary_key` a `PrimaryKey` of its columns and whether it was given. The format
  of the profile is raised to 13.2.
- **Candidates of one column:** of no nulls and no sentinels, of a type that identifies a row -
  no floating point, no time, no boolean, binary or structure, as the dialect says -, of an
  approximate distinct count of at least 98 % of the rows, the first indication, and unique in the
  sample.
- **Candidates of two columns**, of the same kinds, neither a key alone: each with values twice in
  the sample, which the pair tells apart, unique in the sample, and of distinct counts whose
  product reaches the rows. The ten whose product lies closest to the rows are verified, as natural
  keys lie close to them; tables of more than 200 columns are not tried blindly. Three columns are
  left for later.
- **Verified on the whole table** by exact distinct counts, `count(DISTINCT ROW(a, b))`, built from
  the building blocks of the dialect as the statistics are, and compared with the rows counted in
  the same query; ten candidates at most in one query, as Trino holds the values of each count in
  memory. The standard error of the approximate distinct counts is the dialect's.
- **The primary key:** given by the overrides, else of the keys the one of the fewest columns, then
  of whole numbers or UUIDs, then the first in the table; the readings of the names are not used,
  as `describe` reads them after `scan`.
- **A key given** that is not unique is warned of and kept as the primary key; it is not among the
  keys, which the report shows. Keys of an entity are left to the overrides.
- **The simulation** makes a key of two columns unique, the column of fewer values numbered within
  the other; the example has `(ord_id, pos_no)` of `ord_itm`.

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
- **2026-11-05** — The interface agreed with the maintainer (see How): keys of one and two columns,
  the candidates indicated by the approximate distinct counts and the sample, as tables have up to
  200 columns, and ten at most verified in one query.
- **2026-11-05** — Step 1 built: the keys of one and two columns found by `scan` - the candidates
  indicated, verified by `Dialect.exactly_distinct`, ten at most a query -, the primary key chosen
  among them, held by the profile, shown by the report, and generated by the simulation, whose items
  of an order have the key `(ord_id, pos_no)`. Whether a primary key was given is held from step 2
  on, which gives it.
- **2026-11-05** — After the review, the maintainer decided: the candidates are verified by exact
  distinct counts compared with the rows, rather than by a statement of its own counting the values
  of more than one row, which Trino plans the same way; and the dialect names the standard error of
  its approximate distinct counts, `Dialect.distinct_error`, which `keys` and the tests of `scan`
  take.
