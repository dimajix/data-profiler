# 23 — Sentinel values

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Scan
**Summary:** A value that stands for no value - an empty text, `00000`, `9999-12-31` - is counted as a value like any other, so that a column of them looks filled, its range runs to the sentinel, and its share of a semantic type falls below the threshold.

## The problem

Only `NULL` is no value today. Many databases fill what is not given with a value of their own: an
empty text or spaces, `-`, `00000` for a postal code, `1900-01-01` or `9999-12-31` for a date. Such
a value, a sentinel, is counted as a value everywhere:

- **Statistics.** `Statistics.nulls` counts the nulls alone; a column of 62 % empty texts is told
  as filled in nearly every row.
- **Detection.** `detect.detect` cuts the spaces of each value and keeps the empty texts it is left
  with among the values it divides by. A column of postal codes, 62 % of it empty, has a share of
  0.38 of `postal-code`, below the threshold of one half, and no match. This is wrong today,
  whatever else this issue decides.
- **Ranges.** The smallest or largest value of a column is the sentinel: `9999-12-31` as the end of
  every validity, `00000` as the smallest postal code.
- **Verification.** `matching.verify` counts the values that are not null on the whole table, the
  sentinels among them, so that the share on the table falls as the share of the sample does.

## Why it matters

What the language model is shown of a column - how often it is filled, its range, its matches -
is wrong where a column has a sentinel, and many columns of an old database have one. The groups of
columns filled together ([25](25-groups-of-columns-filled-together.md)) need it first: a column
filled with empty texts by default would be filled in every row, and its group lost.

## What is to be decided

The interface first, put before the maintainer.

- **The empty text first, on its own.** A text that is empty once its spaces are cut is no value of
  any semantic type; `detect` leaves it aside as it leaves the nulls. It is the smallest step, and
  could be done before the rest.
- **Which sentinels there are.** Options, not exclusive:
  - a fixed set of the tool: the empty text, `-`, a run of zeros;
  - sentinels of a semantic type: `1900-01-01` and `9999-12-31` of a date, `00000` of a postal
    code - given where the type is, in `detect`;
  - sentinels found in the sample: a value far more frequent than the others that is not of the
    type the column matches;
  - sentinels of a project, given in `project.yml` as its semantic types are
    ([16](16-semantic-types-of-a-project.md)).
- **What is counted on the whole table.** The rows of each sentinel of a column, by the query of the
  statistics, built from the building blocks of the dialect; whether the range and the lengths
  leave the sentinels out, and the share `verify` counts does.
- **What the profile holds.** The sentinels of a column with their rows, such as
  `sentinels: [{value: "00000", rows: 1204}]` beside `nulls`, in the form of `Value`; the format of
  the profile is raised.
- **Disclosure.** A sentinel is a value of the column. One of the fixed set is no value of a
  person and may always be shown; one found in the sample of a sensitive column may be a real
  value - the most frequent phone number -, and goes into the profile only as `disclosure` lets it.
- **Where it lives.** Recognising a sentinel is close to recognising a semantic type (`detect`),
  counting it close to counting the nulls (`statistics`); which part owns the concept is to be
  drawn in `docs/ARCHITECTURE.md`.

## Done when

- The interface is agreed with the maintainer.
- A column of postal codes with a majority of empty texts is a match of `postal-code`.
- The sentinels of a column are counted on the whole table and named in the profile, its range
  without them.
- The simulation can generate a column with a sentinel, and a test against it finds it.

## History

- **2026-11-03** — Opened from the comparison with an earlier draft of a profile, which held the
  sentinels of each column; found along the way that empty texts keep a column from its match.
