# 26 — Overrides read by scan

**Status:** open
**Type:** bug
**Priority:** high
**Area:** Profile
**Summary:** A profile written by scan holds the range and the values of the columns an override marks sensitive, as scan does not read the overrides, so that the profile, which is shared, holds what the overrides were to withhold.

## The problem

`scan` never reads the overrides ([11](11-overrides.md), `docs/ARCHITECTURE.md`, "The domain"):
it discloses each table by the matches of its columns alone, and `report` lays the overrides over
the profile it renders. A column the detectors miss but an override marks sensitive keeps its range
and the values of its enumeration in the profile `scan` writes: `cust.cust_nm` of the example
project, marked `personal`, has the first and the last name of a customer in `tables/cust.yml`.
The report withholds them; the profile, which a project keeps in version control and shares, does
not. It breaks the first principle of `docs/ARCHITECTURE.md`: the profile holds no values of the
columns found sensitive, by their matches or where an override marks them so.

## Why it matters

The overrides are the one way to mark what no detector recognises - the names of persons above
all -, and the profile is what is shared. Besides, [23](23-sentinel-values.md) needs the sentinels
of a column, given by hand, where they decide what is counted: in `scan`, which an override laid
over afterwards cannot reach without querying the database again.

## What is to be decided

The interface first, put before the maintainer.

- **The principle.** Every stage takes as given what an override gives of what it does: `scan` the
  sensitivity of a column - and, with [23](23-sentinel-values.md), its sentinels -, `describe` the
  words of terms and the names of columns, `report` all of it. "`scan` never reads it" goes.
- **Where they are laid over.** `scan` lays the overrides of a table over it once it is counted,
  before it is disclosed, so that what is written holds the mark and none of the values;
  `overrides._laid_over` does that for a table today. `report` keeps laying the overrides over the
  profile, so that a mark given after a scan withholds the values in the report without a scan
  again.
- **What is refused, and when.** An override naming a table that is not selected is refused before
  anything is counted; one naming a column the table does not have, once the table is counted.
  The words of terms are not checked by `scan`, which does not use them.
- **Overrides changed during a run.** A run resumed skips the tables it counted, with the overrides
  of then. A mark taken out of `overrides.yml` gives back no values without a scan; a mark added,
  or sentinels changed, leaves a table counted by the run with what it no longer should hold.
  Options: a table whose marks - and sentinels - differ from those the overrides give is not
  counted by the run, and counted again; or a run resumed with other overrides is not resumed, and
  a new one begun.

## Done when

- The interface is agreed with the maintainer.
- A profile written by `scan` holds no range and no values of a column an override marks
  sensitive, and holds the mark.
- An override naming a table that is not selected is refused before anything is counted.
- `docs/ARCHITECTURE.md` and the module docs of `overrides` say which stage takes what as given.

## History

- **2026-11-03** — Opened while planning [23](23-sentinel-values.md), whose sentinels are given by
  hand per column; the maintainer decided that `scan` reads the overrides, and that it comes before
  [23](23-sentinel-values.md).
