# 19 — Names of tables that differ in case alone

**Status:** open
**Type:** bug
**Priority:** low
**Area:** Profile
**Summary:** Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do.

## The problem

The names of tables become names of files: of the profile, a file of each table in `tables/`
([18](18-a-scan-written-table-by-table.md)), and of the workspace, a sample and the enumerations
of each table. `files.is_file_name` checks each name on its own - its characters, the names
Windows reserves -, but not two names against each other. A file system that ignores case takes
`Cust.yml` and `cust.yml` for one file: the second table overwrites the first, and a checkout of a
profile shared by version control has one of them alone.

## Why it matters

Little, for now: Trino names its tables in lower case, so a schema read through Trino has no two
such names. It matters once a dialect of a database that keeps the case of names is added, as the
cut of `Dialect` allows.

## What is to be decided

- **Refused or told apart.** A profile whose tables collide when case is ignored is refused when it
  is written, naming both; or the names of the files tell them apart, such as by an encoding of
  the upper case letters, which a person reading `tables/` would have to decode.
- **Where it is checked.** Once, for the profile and the workspace alike, beside `is_file_name` in
  `data_profiler.files`, which checks a single name today.

## Done when

- Two tables whose names differ in case alone are refused or kept apart, in the profile and in the
  workspace alike.

## History

- **2026-11-02** — Opened from the review of step 1 of
  [18](18-a-scan-written-table-by-table.md), which made the profile a file per table; the
  maintainer decided to settle it in an issue of its own.
