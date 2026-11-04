# 33 — Major and minor versions of the formats

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Architecture
**Summary:** The version of a format is raised with every change to its fields, and a document of another version is refused, so that a field added as optional makes every profile be scanned again and every `overrides.yml` and `project.yml` be edited by hand, though the document the version before wrote is read as it was.

## The problem

The profile, the overrides and the configuration of a project are documents of a format each, and
its version is one number: `profile.FORMAT`, `overrides._FORMAT`, `project.FORMAT`. It is raised
with every change to the fields of the classes a document holds, and `documents.read_document`
refuses a document of any other version, an older one as well. A profile of an older version is
removed and scanned again; overrides and a configuration, which a person writes, are edited by hand
to the new version.

Most of the raises so far added a field, or gave one a default, which a document of the version
before is read with as it was:

| Raise | Change |
|---|---|
| profile 10 → 11 | `name_given`, optional ([10](10-the-stage-describe.md)) |
| profile 11 → 12, overrides 5 → 6 | `abbreviations` of a concept optional ([29](29-the-word-of-a-concept-as-a-term.md)) |
| profile 12 → 13, overrides 6 → 7 | `description` of the database and of a table, optional ([32](32-descriptions-of-the-database-and-its-tables.md)) |

None of them needed a scan or an edit; each asked for one.

## Why it matters

A scan reads the database anew, which takes long on a large one; an edit of `overrides.yml` is asked
of every person on every update, for nothing that changed for them. Profiles are kept in version
control and shared, so that a person whose tool is older than the one that wrote a profile has to be
told so, and not be shown a field they do not know.

## What is decided

As discussed with the maintainer:

- **A version of two parts**, major and minor. The major version is raised with a change that is
  incompatible, and the minor version set to 0; the minor version is raised with a change that is
  compatible.
- **Incompatible** is: a field added that is required, a field renamed or removed, a default
  changed - a default is not written, so that a document of the version before would be read with
  another value, unseen -, the type or the meaning of a field changed, and, for the profile, the
  files it is written to changed.
- **Compatible** is: a field added that is optional, and a required field made optional.
- **Reading:** a document of the same major version and a minor version not above that of the tool
  is read, what it lacks taken by its defaults. One of a minor version above that of the tool is
  refused, naming both versions and saying that the tool is older than the document: unknown
  fields stay refused (`extra="forbid"`), as they tell a field written amiss in a document written
  by hand. One of another major version is refused as now; a profile is removed and scanned again,
  not converted.
- **Writing:** `format: "13.1"`, a string, as YAML reads `13.1` as a number, of which `13.10` is
  `13.1`. A plain `format: 13` is read as `13.0`, so that every document written so far stays
  valid, and the change of scheme costs no one a scan or an edit.
- **One place:** `documents.read_document` and `documents.write_document`, which the three
  documents share; each holds its version as a pair, `FORMAT = (13, 0)`, and the doc comments of
  the three constants state the rule once, the others pointing to it, as they do now.

## Done when

- The three documents are read and written by versions of two parts, as decided.
- A document of the same version, of an older minor version, of a newer minor version and of
  another major version are each tested.
- The rule is stated in the doc comment of `profile.FORMAT`, and the documents that name it agree.

## History

- **2026-11-04** — Opened, as the maintainer decided: the version is raised only by incompatible
  changes as its major part, by compatible ones as its minor part.
