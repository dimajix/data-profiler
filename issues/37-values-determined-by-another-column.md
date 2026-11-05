# 37 — Values determined by another column

**Status:** open
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

## Done when

- The interface is agreed with the maintainer.
- The dependencies of a table of the simulation are found and verified on the whole table.
- The report shows them.

## History

- **2026-11-05** — Opened with [38](38-a-data-model-derived-from-the-profile-epic.md), as agreed
  with the maintainer: normalizing is a step of its own beside the split of a table into its
  entities, and of lower priority.
