# 37 — Values determined by another column

**Status:** in progress
**Type:** feature
**Priority:** low
**Area:** Scan
**Epic:** [38](38-a-data-model-derived-from-the-profile-epic.md)
**Summary:** Nothing tells which columns of a table are determined by another column than its key - the name of a customer repeated in each of its orders -, so that values copied from another entity, which a normalized model holds once, are not seen.

## The problem

A column whose value follows from another column than the key - `cust_nm` from `cust_id` in
`ord`, the city from the postal code - holds the same value again in every row of the other: a
functional dependency. The profile does not say so, and a data model derived from it keeps the
copy as an attribute of its own.

## Why it matters

Normalizing a table takes the columns determined by another into an entity of their own, the other
as its key. It is a step of the model beside the split of the rows into the entities of a table
([36](36-entities-of-a-table.md)), which comes first: within the rows of one entity, a dependency
is seen that the others hide. Where the column the others follow from refers to a table
([35](35-references-between-tables.md)), the columns that follow are copies of the columns of that
table.

## What is to be decided

The interface first, put before the maintainer.

- **The candidates.** A dependency of one column on one other, in the first version: of a column
  that is no key ([34](34-primary-keys.md)), whose values repeat, on which another depends where
  each of its values comes with one value of the other. Dependencies on several columns grow with
  the combinations of them; whether they are needed.
- **Found in the sample.** Each value of the one with the values of the other it comes with in the
  sample. A value that comes once in the sample says nothing; whether a dependency needs a share of
  values of the sample that come with several rows.
- **Verified on the whole table.** By a query that counts the values of the one that come with more
  than one value of the other, built from the building blocks of the dialect. Real data hold
  exceptions - a name corrected in later orders alone -, so that the profile holds how strictly it
  holds, as a share.
- **What the profile holds.** In the document of the table, each dependency with the column the
  others follow from, the columns that follow, and how strictly; within an entity of the table,
  where it has entities.
- **What the overrides give.** A dependency found that is none, rejected.
- **The report** shows the dependencies of each table.

## How

As decided with the maintainer, in three steps - the attributes of a table renamed, the
dependencies found, then those the overrides reject:

- **Names.** The attributes of a table about its columns are named after them: `column_groups`, of
  the type `ColumnGroup`, and `column_dependencies`, of the type `ColumnDependency`; the references
  of which several keys may be the one are `reference_candidates`. The format of the profile is
  raised to 14.0.
- **Where.** In `scan`, by the new module `dependencies`, after the column groups: found in the
  sample as `grouping` finds the groups, verified on the whole table as `keys` verifies the keys.
  Not `relate`: a dependency lies within one table.
- **Apart from the column groups.** A group tells which columns are filled in the same rows; a
  dependency tells which values follow from the value of another column. A dependency is found in
  the rows its determinant is filled in alone, as `detect.is_filled` says; a null of a dependent
  there counts as a value.
- **The candidates.** One determinant, no key and not constant, filled in ten rows of the sample at
  least, half of them with a value that repeats; a dependent that is no key and not constant. A
  dependency holds in the sample where at most 1 % of the rows depart from it.
- **One dependency, many dependents.** All the columns that follow from one determinant are one
  dependency; determinants that follow from each other - a code and its name - are equivalent and
  held together, which needs no query: the one follows from the other, and both have as many
  values. A table that holds a table it refers to joined in has one dependency of all its columns.
- **Verified** on the whole table by exact distinct counts, ten expressions at most in a query, as
  the keys are: the values of the determinant against those of the determinant and its dependents
  together, one expression of a whole dependency; where that falls short, each dependent alone. Its
  strictness is 1 - (distinct of all - distinct of the determinant) / distinct of the determinant,
  and a dependency is held from 0.95 on. The 50 dependencies of the most dependents, then of the
  most evidence in the sample, are verified, the others logged.
- **What the profile holds:** `ColumnDependency` of its determinants, its dependents and its
  strictness, over the whole table, not within its entities. Transitive dependencies are held as
  they are found; a minimal cover is left to the data model.
- **The overrides** reject all the dependencies of a column as determinant, in the first version.
- **The report** shows the dependencies of each table below its column groups, and marks a
  determinant that is a reference.
- **The simulation** copies the name of the customer into `ord`, and joins a small reference table
  of a code and its name into a table.

## Done when

- The interface is agreed with the maintainer.
- The dependencies of a table of the simulation are found and verified on the whole table.
- The report shows them.

## History

- **2026-11-05** — Opened with [38](38-a-data-model-derived-from-the-profile-epic.md), as agreed
  with the maintainer: normalizing is a step of its own beside the split of a table into its
  entities, and of lower priority.
- **2026-11-06** — Decided with the maintainer (see How). Step 1 built: the column groups and the
  reference candidates of a table renamed, the format of the profile raised to 14.0.
- **2026-11-06** — `Dialect.exactly_distinct` takes expressions, counted in the rows the first is
  not null in, as a step of its own before the dependencies.
- **2026-11-06** — Step 2 built: `ColumnDependency` and `Table.column_dependencies`, the format of
  the profile raised to 14.1; the new module `dependencies`, called by `scan` after the column
  groups; the report; the simulation makes a column that follows from another of its values, and
  `ord` copies the name of the customer, `ord_itm` the group of the product, its code and its name.
  A dependent that departs from a constant, in the rows of the values of its determinant that
  repeat, no more than it may depart from the determinant follows from it by no dependency: the
  simulation showed it, a column of another entity null in all of them. A key of one column needs
  no rule of its own: its values do not repeat, and depart from every determinant.
