# 40 — Overrides in several files

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Profile
**Summary:** The overrides of a project are one file, `overrides.yml`, which grows with every table corrected and every concept given, so that a database of many tables has overrides of thousands of lines that cannot be split by subject - a glossary apart from the tables, a group of tables apart from the others - and that two developers correcting different tables change in the same file.

## The problem

`Project.overrides` names one file, `overrides.yml` in the directory of the project, and
`Overrides.read` reads it, or gives no overrides where there is none. Everything given by hand - the
description of the database, the glossary, and what is given of every table and its columns - stands
in that one file.

## Why it matters

The overrides grow with the database: a concept for every term, a reading, a name or a description
for every table and column the tool got wrong, the sensitivity of the columns it did not find. A
file of thousands of lines is hard to find one's way in, and cannot be kept by subject: the glossary
in a file of its own, the tables of one area of the business in another. Two developers who correct
different tables change the same file, and their changes collide in a merge more often than they
would in files of their own.

## What is wanted

As the maintainer asked: beside `overrides.yml`, a directory `overrides/` in the directory of the
project, all of whose files of YAML are read and merged into the overrides of the project. A project
may have both, either of them, or neither:

| The project has | Its overrides are |
|---|---|
| neither | none, as today without `overrides.yml` |
| `overrides.yml` alone | those of the file, as today |
| `overrides/` alone | those of all its files, merged |
| both | those of the file and of all files of the directory, merged |

## What is to be decided

- **How files are merged, and what one given twice is.** The maps - `tables`, their `columns`, the
  `glossary`, the `entities` of a discriminator - are merged key by key, so that one file can give
  the readings of a table and another its sensitivities. What one field given in two files is, is
  open:
  - *refused, naming both files* - the merge does not depend on the order of the files, and nothing
    given is silently lost. Recommended.
  - *the later file wins*, in an order of the names of the files - allows defaults to be overridden,
    but makes the order of names a rule a person has to know, and hides a correction given twice.
  - Whether a concept of the glossary, or an entity, is one value given whole by one file, or merged
    field by field like a table, belongs to the same decision; whole is simpler, and a concept is
    small.
- **Which files are read.** `overrides.yml` and the files of the profile are named `.yml`; the files
  of the directory would be read by the same extension, `*.yml`, for one name throughout - or
  `*.yml` and `*.yaml` alike. Files of its subdirectories: read as well, so that tables can be
  grouped further, or not. Files of another extension are ignored, or refused so that a misnamed
  file is seen.
- **The version of the format.** Every file is a document of its own and names its version,
  `format:`, as `overrides.yml` does today, so that each is read by `Format.read` as now, its errors
  naming the file; the merge comes after.
- **Where the file of an error is named.** An error of reading names its file, as now. What the
  stages refuse or warn of of the merged overrides - a table that is not profiled, a reading of the
  wrong number of words - names the table and column, not the file it was given in; finding it is a
  search of the directory. Whether the file is worth carrying to every refusal, or the name of the
  table is enough, is to be decided.
- **Who owns what.** `Project.overrides` names one file today; it would name the overrides of the
  project - the file and the directory -, and `Overrides.read` would read and merge them, or a
  function beside it. Which interface, and whether the merge is a method of `Overrides` and of each
  override class, is put before the maintainer as the plan of the work.

## What is decided

As the maintainer decided:

- **A field given in two files is refused**, naming the field and both files, whatever each gives -
  also the same value twice.
- **The files are merged as the documents give them**, before the classes take their defaults:
  maps key by key, every other value - a list, `false` - a field of its own. Merging the classes
  instead was rejected, as a default no longer tells a field given as its default -
  `omitted: false` - from one not given, and every class of the overrides would need a merge of
  its own.
- **`documents` merges**, by `Format.read_merged(paths)`: each document is read and checked by
  itself, as `Format.read` reads it, so that an error of a field names its file; then the documents
  are merged, and the merged one is checked once more. As each is checked by itself, a
  discriminator and a reference, which have fields that are required, are given whole in one file.
  Merging in `overrides` was rejected, as it would need the step between reading the version and
  checking the fields that `Format` owns.
- **`Project.overrides` names the files**, `overrides.yml` and the files `*.yml` of `overrides/`,
  those there are, the file first and those of the directory by their names; `Overrides.read(paths)`
  reads them merged, none where there are none. Subdirectories and files of other names, `.yaml`
  among them, are ignored.
- **Each file names its own version**, `format:`, and is read by it.
- **What the stages refuse or warn of names no file** for now, only the table and the column.

## Done when

- The overrides of a project are read from `overrides.yml`, from all files of `overrides/`, from
  both or from neither, as the table above says, by every stage.
- What one field given in two files is behaves as decided, and is tested.
- `docs/PROJECT.md` describes the directory of the project with `overrides/`, how its files are
  merged and what is refused, and its reference and recipes say that they hold of every file of the
  overrides; the README and `docs/ARCHITECTURE.md` where they name `overrides.yml` alone.

## History

- **2026-11-06** — Opened, as the maintainer asked: the overrides split into the files of a
  directory `overrides/`, beside or in place of `overrides.yml`.

- **2026-11-06** — Done as decided: `Format.read_merged` in `documents`, `Overrides.read` of the
  files `Project.overrides` names, `docs/PROJECT.md` with the files of the overrides and how they
  are merged; the README and `docs/ARCHITECTURE.md` name the directory beside `overrides.yml`.
