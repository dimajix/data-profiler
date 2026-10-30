# 11 — Overrides

**Status:** open
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
