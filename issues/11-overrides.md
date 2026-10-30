# 11 — Overrides

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Profile
**Epic:** [02](02-first-version-epic.md)
**Summary:** A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe.

## The problem

[01](01-initial-project-setup.md) decided that corrections are overrides: a part of a profile,
written by hand, laid over the generated profile - not a format of their own. What an override sets
is taken as given, by `describe` as by `report` (`docs/ARCHITECTURE.md`, "The domain"). Nothing
reads or lays them yet.

## Why it matters

A small model will propose wrong words. A correction of one term's word in the glossary corrects
every column that has the term - but only if it survives the next run.

## What is to be decided

The interface first, put before the maintainer.

- **How a part of a profile is told apart.** The same schema with every field optional, or a
  schema of its own that mirrors it; the first keeps one format.
- **How it is laid over.** By the keys of tables, columns and terms; what an override names that
  the profile does not have is an error, naming it.
- **What may be overridden.** At first the words of terms and the suggestions of columns - what a
  person corrects -, and the sensitivity of a column the detectors miss ([08](08-detection.md));
  more once someone needs it.
- **Sensitivity, decided with the maintainer during [08](08-detection.md).** `scan` judges the
  sensitivity of a column by the matches of the detectors alone, and never reads overrides. A
  column an override marks sensitive loses its values - its range, the values of its enumeration -
  where the override is laid over the profile, by `describe` as by `report`, through
  `data_profiler.disclosure`, the one place that decides what of the values goes into the profile;
  a mark needs no scan again.

## How

As decided with the maintainer:

- **A document of its own**, not the schema of the profile with every field optional: the
  overrides of a project are `overrides.yml` in its directory, the same for all its environments,
  of a format of their own; tables, columns and terms are keys, by their original names, so that a
  person writes no more than what is given. Where there is no file, there are no overrides.
- **The interface:** `Overrides` - the glossary, and the tables with what is given of their
  columns, `TableOverride` and `ColumnOverride` -, read by `Overrides.read` and laid over a
  profile by `laid_over`, refusing with `OverridesError` what names a table, column or term the
  profile does not have; `Project.overrides`, the path of the file.
- **Sensitivity:** a column has the sensitivity given by hand, `Column.marked`, before that of its
  matches; `laid_over` discloses the table again, so that a column marked sensitive loses its
  values. Marked of none, it gets no values back: `scan`, which removed them, never reads
  overrides.
- **Suggestions** are overridden once [10](10-the-stage-describe.md) makes them; `describe` and
  [12](12-the-stage-report.md) call `laid_over` when they are made.

## Done when

- The interface is agreed with the maintainer.
- `describe` takes the words and names of an override as given and proposes the rest; `report`
  shows the profile with the override laid over it.
- An override naming a table, column or term the profile does not have is refused with a message
  naming it.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-30** — The sensitivity of a column added to what may be overridden, as the maintainer
  decided while [08](08-detection.md) was made: applied by the stages that lay overrides over the
  profile, not by `scan`.

- **2026-10-30** — The interface agreed with the maintainer, and made: `data_profiler.overrides`,
  `Column.marked` in the profile, of format 4, and `Project.overrides`; `disclose` keeps the values
  a column of a profile has where no enumeration is given, so that `laid_over` can disclose a
  table of a profile again. The example project has its overrides, which mark the names of persons
  sensitive. The issue stays in progress: what it is done by - `describe` and `report` laying the
  overrides over - comes with [10](10-the-stage-describe.md) and [12](12-the-stage-report.md).
  After the review: `disclose` takes a table alone, and keeps what it may of the range and the
  values each column holds, so that it has one meaning - what a table may keep - and a table
  disclosed again is disclosed as before; `scan` gives the columns of an enumeration their values
  before it discloses the table. The version of the format of the overrides is private, as no one
  outside reads it. Two details differ from the interface agreed, for the maintainer's review:
  `Overrides.read` returns `Overrides`, as `Profile.read` returns `Profile`, since the document it
  reads is of that class; and a message of `laid_over` names what is wrong, but not the file, which
  the overrides do not keep once read. To be settled with [10](10-the-stage-describe.md): a stage
  that writes the profile it laid the overrides over keeps their marks in it, so that a mark taken
  out of `overrides.yml` stays until the next `scan`, unless the stage lays them over the profile
  `scan` wrote.
