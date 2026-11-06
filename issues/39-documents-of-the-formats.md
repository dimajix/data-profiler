# 39 — Documents of the formats, generated from the code

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Profile
**Summary:** The formats of `project.yml`, `overrides.yml` and the profile are described only in the prose of the README and in doc comments, without a reference of their fields and without examples of what a person writes, so that a developer writing overrides reads the code to learn what a field takes, and a description written by hand would drift from the classes it describes.

## The problem

A developer of a project writes `project.yml` and `overrides.yml`; a person reading a profile reads
its documents. What each field of them takes - its type, whether it is required, what it means - is
said in the doc comments of the classes the documents hold, and nowhere else in one piece: the
README describes both files in two long paragraphs of prose, `docs/ARCHITECTURE.md` describes
overrides and the profile in its domain, and the module docs of `overrides` hold the rules of how
each override is taken. Examples are the two files of `examples/crm/`, whose comments describe them
as a whole, not entry by entry.

## Why it matters

What a person writes by hand is learnt best from examples of a task - marking a column, giving a
primary key, suppressing a reference - next to a reference of every field. A reference written by
hand drifts from the classes: every field added, as issue
[33](33-major-and-minor-versions-of-the-formats.md) lists them, would have to be added there too,
and nothing would tell that it was not.

## What is decided

As discussed with the maintainer:

- **The concept `Format`** in `documents`: the class a document of a format holds and the version of
  its fields, which read and write it - in place of `read_document` and `write_document`, which take
  the two apart at every call. Each owner offers its format: `project.FORMAT`, `overrides.FORMAT`,
  `profile.HEAD` and `profile.TABLE`, the two formats of the profile of one version,
  `profile.VERSION`. A refactoring of its own, without a change of behaviour, before the rest.
- **Two documents**, `docs/PROJECT.md` of the configuration of a project and its overrides, and
  `docs/PROFILE.md` of the profile: what holds, written by hand, and a reference of the fields of
  each format, generated from the classes - their fields, types, defaults and the descriptions of
  their doc comments, the whole description of each class -, between markers in the document. No
  decorators and no other comments in the code: the doc comments are the one source.
- **The generator** is `scripts/formats.py`, a tool of the repository, not of the tool: with
  `--check` it fails where a document is not what it would write; the pre-commit hook writes the
  documents anew when code is part of a commit, as it does the issue overviews, and a test fails
  where they are not up to date.
- **Recipes** in `docs/PROJECT.md`: an example of each task, a snippet of `project.yml` or
  `overrides.yml` with comments, read by a test with the format it names, and the snippets of the
  overrides laid over the example profile `simulation/profiles/crm`, so that a snippet that names
  what the profile does not have fails.
- **The example files** `examples/crm/project.yml` and `examples/crm/overrides.yml`, commented entry
  by entry, and documents of the example profile, are put into the documents by the generator.
- **What moves:** the descriptions of both files in the README and the details of overrides and of
  the profile in `docs/ARCHITECTURE.md` move into the new documents, not copied; the rules of the
  module docs of `overrides` that belong into a document are moved there.

Rejected: examples in a section `Example:` of the doc comments, as the example of one class does not
show where in a file it stands, and `Concept` is of two formats; generated files of their own beside
the documents, as a subject is read in one document; making the private classes of the documents
public for the generator, which would widen their visibility for a tool and leave the class and the
version of a format apart.

## Done when

- `Format` reads and writes every document, in a step of its own.
- `docs/PROJECT.md` and `docs/PROFILE.md` hold what holds and the generated reference; the recipes
  and the example files are in them, and tested.
- The checks fail where a document is not up to date; the hook writes them anew.
- The README and `docs/ARCHITECTURE.md` point to the new documents; AGENTS.md and the list of
  documents name them.

Beyond this issue: JSON schemas of the formats, generated from the same classes, would give an
editor completion and checks of `project.yml` and `overrides.yml`; an issue of its own, once wanted.

## History

- **2026-11-06** — Opened, as the maintainer decided: the formats documented from their classes,
  with recipes and example files, all checked against the code.

- **2026-11-06** — Step 1, the refactoring: `documents.Format` reads and writes every document, in
  place of `read_document` and `write_document`; the version of the profile, of both its formats, is
  `profile.VERSION`. The formats stay private in this step - `project._FORMAT`, `overrides._FORMAT`,
  `profile._HEAD_FORMAT` and `profile._TABLE_FORMAT` -, as is what a format holds, as nothing
  outside their modules uses them yet; step 2 makes them public with the generator, their first
  user, the formats of the profile as `HEAD_FORMAT` and `TABLE_FORMAT` rather than `HEAD` and
  `TABLE`, as `_HEAD` names the file `profile.yml` already.

- **2026-11-06** — Step 2, the documents: `scripts/generate.py` writes the references of the four
  formats - `project.FORMAT`, `overrides.FORMAT`, `profile.HEAD_FORMAT` and `profile.TABLE_FORMAT`,
  public now, as is what a format holds - and the example files into `docs/PROJECT.md` and
  `docs/PROFILE.md`, between markers; `tests/test_generate.py` tests it and fails where a document
  is not up to date, `tests/test_recipes.py` reads every recipe and lays those of the overrides over
  the example profile. The classes of the documents that had no `Attributes:` have them, and the
  types of a validator of their own name what they read, by `json_schema_input_type`. Unlike
  decided, the generator is named `generate`, not `formats`, as it writes every generated part of a
  document - files as well as references -, as `issues/generate.sh` writes the overviews; and the
  pre-commit hook checks the generated parts rather than writing them, as writing would add to the
  commit what is not staged of a document, the generator reading the working tree. Which step fills
  which attribute of the profile moved from the module docs of `profile` into `docs/PROFILE.md`; the
  descriptions of both files moved from the README, the details of overrides from
  `docs/ARCHITECTURE.md`, into `docs/PROJECT.md`. The rules in the module docs of `overrides` are
  not moved yet, and stated in `docs/PROJECT.md` as well; where they live is left to the
  maintainer.
