# 03 — The profile

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Profile
**Epic:** [02](02-first-version-epic.md)
**Summary:** There is no profile yet: the stages have no format in which to hand on what they found about a database.

## The problem

The profile is the only thing the stages hand to each other besides the workspace
(`docs/ARCHITECTURE.md`): `scan` writes it, `describe` reads and extends it, `report` reads it, and
a person can read it, share it and correct it. Neither its schema nor reading and writing it exist.

## Why it matters

Every other part depends on it, and its format is a contract: a profile written by one version is
read by the next, and overrides ([11](11-overrides.md)) are written by hand in the same format. A
change to it later costs more than any other.

## What is to be decided

The interface first, put before the maintainer: the classes of the profile and the functions that
read and write it, each with a one-line doc comment.

- **What it holds at first.** Only what its first user writes: the database, its tables and their
  columns, with their original names and types, and the statistics of [07](07-the-stage-scan.md).
  Matches, the glossary, suggestions come with the issues that write them; the schema grows with
  its users, not ahead of them.
- **How it is modelled.** Pydantic models, which validate what is read and give the YAML its form,
  or frozen dataclasses with conversion written by hand. Recommendation: pydantic, since a profile
  is read from a file a person may have edited, and every field has to be checked; the mypy plugin
  of pydantic comes with it.
- **The YAML library.** PyYAML, reading with `safe_load` and writing with `safe_dump`, or
  ruamel.yaml, which keeps comments and order when a file is written back. Recommendation: PyYAML,
  since the tool writes profiles whole and never edits a file a person wrote.
- **Its version.** A field with the version of the format, so that a profile of another version is
  refused with a message naming both, rather than read wrongly.
- **Writing.** Whole or not at all, by a temporary file that takes the place of the profile
  (`docs/CODING-GUIDELINES.md`, "Files are written whole").

## Done when

- The interface is agreed with the maintainer.
- A profile written and read again is unchanged; a profile of another version, or with a field
  missing or unknown, is refused with a message that names it.
- A profile is written whole or not at all.
- `docs/ARCHITECTURE.md` names the classes of the profile where a reader needs them.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-29** — Interface agreed with the maintainer and implemented in
  `data_profiler.profile`. A profile describes one schema: `catalog` and `schema` belong to it, and
  its tables carry only their names, as the URL of a Trino database names one schema. `read` and
  `write` are methods of `Profile`, which owns its format. Its classes are frozen dataclasses of the
  standard library, as the guidelines have states; pydantic validates them at the boundary alone,
  in `read`, and refuses an unknown field - a deviation from "Pydantic models" above, which also
  avoids that a field `schema` collides with a method of pydantic's `BaseModel`. The profile holds
  no raw values yet: the ranges of numbers and dates and the values of enums come with
  [08](08-detection.md), once sensitivity is known. The rows belong to the table, not to the
  statistics of each column.

- **2026-10-29** — Done. The review tightened what was built: a format that is no number is refused,
  the temporary file is removed on any interruption and made with the permissions the user gives new
  files, and `FORMAT` says when it is raised - with every change to the fields; whether older
  formats are read again is decided when it first changes. Since a profile describes one schema, the
  glossary is one per profile, not one per database: the CRM of the first case lies in one schema,
  as the maintainer confirmed. Left as it is: pydantic reads `"312"` for a number as 312, since a
  strict reading would refuse the YAML lists of the tuples too; and whether `Statistics` becomes
  variants per kind of column is decided with [08](08-detection.md), which adds the ranges of
  numbers and dates beside the lengths of texts.
