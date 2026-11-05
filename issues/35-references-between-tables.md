# 35 — References between tables

**Status:** open
**Type:** feature
**Priority:** high
**Area:** Scan
**Epic:** [38](38-a-data-model-derived-from-the-profile-epic.md)
**Summary:** Nothing tells which columns of a table refer to the key of another - the customer of an order -, so that the relationships between the tables, which a data model is made of, are left to a person to find.

## The problem

The tables of the CRM declare no foreign keys, and Trino would name none. That `ord.cust_id` holds
the identifiers of `cust`, a person reads from the names, if the names are readable, and checks
nowhere. The epic of the first version left the relationships between tables out
([02](02-first-version-epic.md)).

## Why it matters

A reference is what makes a data model of separate tables: which entity belongs to which, and how
many of the one to one of the other. It is found in the data: a column refers to a key where its
values are among the values of the key - an inclusion dependency.

## What is to be decided

The interface first, put before the maintainer. It needs the keys of
[34](34-primary-keys.md).

- **Where it is found.** The references need the keys of all tables, not of the one counted: they
  are no work of `scan`, which counts table by table. Proposed: a stage of its own after `scan`,
  `relate`, which queries the database and writes the profile, as `scan` does; it would get an area
  of its own. Whether it uses the readings of the names `describe` leaves, if it ran - for the
  order of the candidates alone, so that it runs without `describe` -, and whether `describe` in
  turn shows the language model the references of a column.
- **The candidates.** Each pair of a column and a key of another table - or of the same, a parent
  of a hierarchy - of a type that compares; filtered by the profile, without a query: no more
  distinct values than the key, lengths and matches that agree, a range within the range of the
  key. The ranges are held of the columns of no sensitivity alone; whether those of the others are
  kept in the workspace for it.
- **A check without a query.** The distinct values of every key verified kept in the workspace, as
  Parquet, where sensitive values may be; the values of the sample of a candidate looked up in
  them, and only a candidate whose values are mostly found checked on the whole table. A pair of
  random samples of two tables says nothing: they hold few of the same rows.
- **Verified on the whole table.** By a query that counts the values of the column not found in the
  key, its nulls and sentinels left aside, built from the building blocks of the dialect: the
  coverage, as a share, not a yes or no, since real data hold rows whose reference is lost.
- **Codes that fit every key.** A status code of 1 to 5 lies within every key of integers from 1.
  Whether an enumeration is a candidate only where its name agrees - its reading names the concept
  the table of the key is read as -, or the coverage of the key is weighed: a column whose values
  fill a small part of the key is less likely a reference.
- **What the profile holds.** In the document of the table that refers, each reference with its
  columns, the table and key it refers to, its coverage, and its cardinality: whether one row or
  many refer to one of the key.
- **What the overrides give.** A reference the data do not show, and a reference found that is
  none, rejected, as a concept is omitted. A reference given is counted as one found is: its
  coverage and cardinality come from the data.
- **References to an entity.** In a table of several entities ([36](36-entities-of-a-table.md)),
  `ord.cust_id` may refer to the rows of one entity of `cust` alone; whether the coverage is counted
  per entity of the key.
- **The report** shows the references of each table, and what refers to it.

## Done when

- The interface is agreed with the maintainer.
- The references of the tables of the simulation are found, with their coverage and cardinality,
  and a code of a few values is not taken for a reference.
- The overrides give and reject references.
- The report shows them.

## History

- **2026-11-05** — Opened with [38](38-a-data-model-derived-from-the-profile-epic.md), as agreed
  with the maintainer.
