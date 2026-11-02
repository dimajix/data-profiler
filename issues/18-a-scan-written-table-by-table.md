# 18 — A scan written table by table

**Status:** in progress
**Type:** feature
**Priority:** high
**Area:** Scan
**Summary:** A scan writes its profile only once it has counted every table, so that a run that fails or is interrupted at one table loses all the tables before it, and a new scan replaces the profile whole.

## The problem

`scan` gathers the tables it counts in memory, and the command line writes the profile once, at
the end. A scan of the real database runs for hours - about 20 tables, some of more than 200
columns -; when it fails at the last table, or is interrupted, nothing of it is kept, and it starts
again from the first. A scan that finishes replaces the profile whole, the glossary of `describe`
with it.

The profile of the real database is a file of about 90,000 lines, which a person cannot find their
way in.

## Why it matters

The profile is the work of a run of hours. A failure of one table - a query that times out, a
connection that drops - should cost that table, not the run; and a run that is interrupted should
go on where it stopped.

## What was weighed

- **One file or a file per table.** Written after every table, one file of 90,000 lines costs
  about 1.2 seconds to write and 2.8 to read with PyYAML, 0.3 and 0.8 with libyaml: nothing beside
  the queries, so the cost does not decide. A file per table is chosen for a person to read: one
  table is one file, and its changes are a diff of their own. It costs the profile being one
  document - it becomes a directory -, the files are no longer written together at once, and the
  names of tables become names of files.
- **Who writes the profile.** `scan` takes the directory of the profile and reads and writes it
  itself, rather than handing its tables to the command line by a callback or a generator, which
  would put the rules of a run into the command line or into glue.
- **What identifies a run.** The time it started: unique, as runs of one environment follow each
  other, and it tells a person reading a table when it was counted. A run that has counted every
  selected table is marked finished: without the mark, a run after which tables are added to the
  database could not be told from one that was interrupted, and the next scan would count only the
  new tables.
- **Resumed by itself or by an option.** By itself: a scan resumes a run that has not finished. A
  run that was interrupted is hardly ever to be thrown away, as the tables it counted are current.

## How

As decided with the maintainer:

- **The profile is a directory**, `<environment>/profile/`: `profile.yml` holds its catalog,
  schema, semantic types, glossary and run, and `tables/<table>.yml` each table, each a document of
  the format of the profile. `Profile.read` and `Profile.write` take the directory; `write` first
  removes the files of the tables the profile does not have, then writes `profile.yml`, then the
  tables, so that what an interruption leaves can be read.
- **A name of a table is a name of a file**, checked by one function of `data_profiler.files` for
  the profile and the workspace alike, which refuses also the names Windows reserves (`con`,
  `nul`, ...), as the profile is shared by version control.
- **The profile is updated, not replaced.** `scan` reads the profile there is, keeps the tables
  that are still selected and the glossary, and drops the tables that are deleted or no longer
  selected. It writes the profile after every table. A profile that cannot be read - broken, or of
  another format - is refused, not overwritten; a profile scanned with other semantic types than
  those of the project loses its tables, as their matches may name types it no longer has.
- **Runs.** The profile holds its run - when it started, and when it finished -, and each table the
  start of the run that counted it. A scan resumes the run of the profile where it has not
  finished, skipping the tables it counted; otherwise it starts a new run.

In steps, each reviewed and committed on its own:

1. The profile becomes a directory, a file per table, of a new format, without a change of
   behaviour; the check of a name of a table as a name of a file moves into `data_profiler.files`.
2. `scan` writes the profile itself, after every table, updating the one there is.
3. Runs, and a run resumed.

## Done when

- A scan that fails at a table leaves the profile with the tables counted before it.
- A scan keeps the tables of the profile it does not count again, and drops those no longer
  selected.
- A scan after an interrupted one counts only the tables the interrupted one did not.

## History

- **2026-11-02** — Opened, as the maintainer asked for the profile to be written after every table,
  updated rather than replaced, and a scan to go on where an interrupted one stopped.

- **2026-11-02** — Step 1 done: the profile is a directory, `profile.yml` and a file of each table
  in `tables/`, of format 6; `Environment.profile` is the directory, and `Profile.read` gives the
  tables sorted by name. A file of a table is read with the semantic types of `profile.yml`, which
  `read_document` takes as the beginning of the context of its validators, in place of the
  validator that read the types of the one document first. `is_file_name` of `data_profiler.files`
  checks a name of a table as a name of a file, for the profile and the workspace, and refuses the
  characters and the names Windows refuses as well. The example of the simulation is a directory,
  `simulation/profiles/crm/`, its tables now in the order of their names, which changes the rows
  generated by a seed.
