# 25 — Groups of columns filled together

**Status:** done
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

## How

As decided with the maintainer:

- **What is filled:** a value that is neither null nor one of the sentinels the statistics of its
  column found, as `detect.is_filled` says, which `detect` uses as well.
- **Which columns take part:** those filled in at least ten rows of the sample, and in at most 90 %
  of them. Two columns filled at random in a share p of the rows have a Jaccard index of
  p / (2 - p), which reaches 0.9 from p = 0.947 on: above 90 %, columns would be grouped by chance.
- **How they are grouped:** by hierarchical clustering of complete linkage, cut at the distance
  0.1, so that every two columns of a group are filled together in at least nine of ten of the rows
  either is filled in, and the coherence of a group is 0.9 at least. By a function of its own, in
  the new module `grouping`, without scipy: a few dozen columns need no library.
- **What the profile holds:** `Table.groups`, each a `Group` of its columns, in the order of the
  table, and its coherence, with three digits; the groups in the order of their first columns. The
  format of the profile is raised to 8. Groups that name a column their table does not have, or one
  twice, are refused when the profile is read. How many digits a share found in a sample is written
  with, of a match as of a group, is `profile.DIGITS`.
- **The report** shows the groups of each table below its columns.
- **The simulation** generates the groups of its profile: the columns of a group share the order of
  the rows their nulls and sentinels take, so that the one of more is filled within the rows of the
  others. The table `ord` of the example has a delivery address of a street, a postal code - whose
  empty texts are sentinels - and a city.
- **Left out**, until someone needs them: columns filled within another as groups within groups, a
  name of a group, an override that rejects a group, and the terms of the members as a check, which
  are left to the language model; showing a group to it is part of
  [10](10-the-stage-describe.md).

## Done when

- The interface is agreed with the maintainer.
- The columns of a table filled together are found in its sample and named as a group in the
  profile.
- The simulation can generate columns filled together - today it spreads the nulls of each column
  over the rows at random, on their own -, and a test against it finds their group.

## History

- **2026-11-03** — Opened from the comparison with an earlier draft of a profile, which grouped the
  columns of a table by the rows they are filled in.
- **2026-11-03** — Done as decided with the maintainer (see How): the groups found in the sample by
  `grouping`, held by the tables of the profile, shown in the report and generated by the
  simulation, whose delivery address of `ord` a scan finds as a group.
