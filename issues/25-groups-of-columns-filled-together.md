# 25 — Groups of columns filled together

**Status:** open
**Type:** feature
**Priority:** low
**Area:** Scan
**Summary:** Nothing tells which columns of a table are filled together - the street, postal code and city of a different delivery address -, so that columns that belong together are named and described each on its own.

## The problem

Columns that belong together are mostly filled together: who has a different delivery address has
its street, its postal code and its city, and who has none has none of them. Nothing in the profile
says so; the language model sees each column apart from the others.

## Why it matters

A group of columns tells what none of them tells alone: three columns of a street, a postal code
and a city, filled in the same 38 % of the rows, are an address of its own, not the address of the
customer. It is a finding the language model can name, and a person can check at a glance.

## What is to be decided

The interface first, put before the maintainer.

- **What is filled.** A value that is neither null nor a sentinel: it needs
  [23](23-sentinel-values.md) first, else a column filled with empty texts by default is filled in
  every row.
- **Where it is found.** In the sample, which holds the rows of a table with the values of each
  column at the same place: no query is needed. Found by `scan`, after the sample, as the matches
  are.
- **Which columns take part.** A column filled in nearly every row or in nearly none tells nothing
  of a group; its nulls say so already, and it is left out. A column filled in too few rows of the
  sample to be judged is left out as well - the sample has about 10,000 rows, so that a group of
  0.1 % of the rows is about ten.
- **How they are grouped.** The similarity of two columns as the Jaccard index of the rows they are
  filled in; groups by hierarchical clustering, cut at a distance such as 0.1, so that a group with
  a few rows missing a member is still one. Whether by scipy, a new dependency, or by a function of
  its own, which a few dozen columns allow.
- **Columns filled within another.** A column filled only where another is, but not the other way
  round - an addition to an address -, makes groups within groups; whether in the first version.
- **What the profile holds.** Each group of a table with its columns and its coherence, the mean of
  the Jaccard indexes of its members, in the file of the table, whose format is raised. The group
  holds its columns, and a column does not name its group, so that it is said in one place. A
  group has no name to be told apart by across scans; whether it needs one.
- **What is done with it.** The language model is shown the group of a column, and may propose a
  name of the group ([10](10-the-stage-describe.md)); the report shows the groups. Columns filled
  together by chance - by one form of the application - are findings, not facts; whether an
  override can reject a group.
- **The terms as a check.** Where the members of a group share terms - `lf` and `adr` -, the group
  is more likely one; whether that is shown, or left to the language model.

## Done when

- The interface is agreed with the maintainer.
- The columns of a table filled together are found in its sample and named as a group in the
  profile.
- The simulation can generate columns filled together - today it spreads the nulls of each column
  over the rows at random, on their own -, and a test against it finds their group.

## History

- **2026-11-03** — Opened from the comparison with an earlier draft of a profile, which grouped the
  columns of a table by the rows they are filled in.
