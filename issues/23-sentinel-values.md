# 23 — Sentinel values

**Status:** done
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

## How

As decided with the maintainer:

- **The sentinels of the tool** are one pattern, of `detect`, which Python and SQL read alike,
  matched whole against a value as text, its spaces at either end cut: the empty text, `NULL` and
  `null`, `N/A` and `n/a`, `-`, and the dates `0001-01-01`, `1900-01-01` and `9999-12-31`, also
  written `01.01.0001`, `01.01.1900` and `31.12.9999`, with a time of day or without. No run of
  zeros: `0`, `00` and `000` are codes in some columns.
- **The sentinels of a column given by hand** are given by an override, read by `scan` since
  [26](26-overrides-read-by-scan.md): `sentinels: ["", "00000"]`, a list of values, matched as the
  pattern is, in place of those of the tool, so that `sentinels: []` turns them off for the column.
- **Counted, not named.** The profile holds the number of the sentinels of a column, beside its
  nulls, not which they are: no value goes into the profile, and an enumeration shows them all the
  same. The sentinels are named in the profile, as "Done when" asks, by their number alone.
- **What leaves them aside:** the distinct values, the range and the lengths of the statistics,
  the share of a match in the sample and on the table. The nulls are counted as before, and an
  enumeration keeps the sentinels among its values, as it shows what a column holds.
- **Left out**, until someone needs them: sentinels of a semantic type alone, found in the sample,
  or given for all columns of a project.

In two steps:

1. A refactoring without a change of behaviour: the building blocks of the dialect that count or
   measure values - `nulls`, `distinct`, `smallest`, `largest`, `shortest`, `longest`, `matching` -
   take an expression of the values of a column, as `Dialect.column` writes it, in place of its
   name, so that they can be given the values without the sentinels.
2. The sentinels: their pattern in `detect`, the building block of the values of a column without
   them in the dialect, their number in the statistics, the overrides of a column, the report and
   the simulation.

## Done when

- The interface is agreed with the maintainer.
- A column of postal codes with a majority of empty texts is a match of `postal-code`.
- The sentinels of a column are counted on the whole table and named in the profile, its range
  without them.
- The simulation can generate a column with a sentinel, and a test against it finds it.

## History

- **2026-11-03** — Opened from the comparison with an earlier draft of a profile, which held the
  sentinels of each column; found along the way that empty texts keep a column from its match.

- **2026-11-03** — The decisions above taken with the maintainer, after
  [26](26-overrides-read-by-scan.md) made `scan` read the overrides. Step 1 done: the building
  blocks of the dialect that count or measure values take an expression of the values of a column.

- **2026-11-03** — Step 2 done, as agreed with the maintainer, with one change of the plan above
  decided after the review: the sentinels are texts, compared by `IN`, not a pattern - they are
  constants, and a value given by hand is one; a moment is compared as the text of its day, as
  Trino and Python write the time of a moment each in its own way. `detect.SENTINELS` is the set of
  the sentinels of the tool, `detect.sentinels` those of a column, given or of the tool, and
  `detect.detect` leaves them aside. The dialect counts them, `Dialect.sentinels`, writes the
  values of a column without them, `Dialect.without`, and tells the types it writes as text,
  `Dialect.has_text`: Trino casts no array, map, row or binary to a text, and those have no
  sentinels. The statistics count them, `Statistics.sentinels`, of every column of text, not of
  texts and days alone, as a lookup in a set costs little. Each column holds the sentinels given
  of it it was counted with, `Column.sentinels`; `TableOverride.agrees_with`, the former
  `is_laid_over`, tells a table counted with other sentinels, which a run resumed counts anew, and
  `TableOverride.check_counted` refuses sentinels given of a column of no text. `matching` leaves
  them aside where the statistics counted any. The overrides give them by
  `ColumnOverride.sentinels`; the profile is of format 7, the overrides of format 2. The report
  shows their share, by one function `share` as it writes the end of a range by `end`; the
  simulation makes them, the empty text of a text and `9999-12-31` of a day or a moment, and the
  example profile has three columns of them: `ord.dlvr_pst_cd`, postal codes of which 62 % are
  empty, which the scan finds a match of `postal-code` all the same, `ord.dlvr_dt`, and
  `cust.seg_cd`, an enumeration.
  After the second review: which sentinels the values of a column were counted without is said in
  one place, `Column.left_aside`, which `matching` uses in the sample and on the table;
  `agrees_with` and `check_counted` share one comparison of the sentinels given and counted with;
  `cust.upd_ts` of the example profile has sentinels, so that a moment compared as its day is
  checked against the database; a test of the statistics on a schema made by hand shows that a
  column of no text is counted without the sentinels given of it.

- **2026-11-03** — Changed with the maintainer after the second review: the decision "Counted, not
  named" above is turned round. The profile names each sentinel of a column with its rows,
  `Statistics.sentinels` of `Value`s, the most frequent first, so that a person can check them, of
  every column of text and whatever its sensitivity: the sentinels of the tool are fixed texts, and
  those given are of the overrides. Each is counted by a `Dialect.sentinels` of its own in the query
  of the statistics, the first of the two ways weighed; the other, grouping the sentinels in the
  query of the enumerations, is left for when the cost shows on the real database. An enumeration
  leaves the sentinels aside as it does the nulls, compared by `detect.is_sentinel`, and so does
  its test of values each in one row alone. Besides: `TableOverride.refuse_uncounted`, the former
  `check_counted`, refuses right after the count both a column the table does not have and
  sentinels given of a column of no text; `verify` leaves out the columns of no text, whose matches
  stay unverified.
  After the third review: `Column.left_aside` is the set of the sentinels found in the column, not
  of those it was counted with; `Statistics.sentinel_rows` sums their rows, for the report and the
  simulation; `detect.detect` leaves them aside by `detect.is_sentinel`; `disclosure` and the
  principle of `docs/ARCHITECTURE.md` say that sentinels go into the profile whatever the
  sensitivity; the example profile has `prod.ean_cd`, whose values are each in one row alone
  beside a sentinel that repeats, and is no enumeration.
