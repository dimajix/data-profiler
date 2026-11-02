# 16 — Semantic types of a project

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** The semantic types are fixed in the code, so that a pattern of one database alone - an account number `A` and ten digits - cannot be recognised without changing the tool.

## The problem

`SemanticType` in `data_profiler.detect` is an enumeration: every type, its pattern and its
sensitivity are written in the code, as the UUID of [15](15-a-detector-of-uuids.md) was. A
database has identifiers of its own - an account number of the letter `A` and ten digits,
`A[0-9]{10}` -, which no tool knows in general and which have no place among the types it brings.
A user who needs one has to change the tool.

## Why it matters

The matches are what the language model of [10](10-the-stage-describe.md) names columns from, and
what judges their sensitivity: an account number of a customer that no detector recognises is
neither named as one nor kept out of the profile, unless every column of it is marked by hand.

## What is to be decided

The type is used beyond the detectors, and whatever is given by a project has to reach all of it:

- **The profile.** A match names its type, and a column takes its sensitivity from the type of its
  matches; `describe` and `report` read the profile alone, and need the sensitivity of a type of a
  project as of one of the tool.
- **The disclosure.** Each value that goes into the profile is checked by every type on its own,
  `detect.is_sensitive`, by `scan` and again where overrides are laid over a profile.
- **Where they are given.** In `project.yml`, as `scan` recognises the types and never reads
  `overrides.yml` (`docs/ARCHITECTURE.md`, Principles).
- **The simulation.** The generator makes values of each type by code of its own; it cannot make
  them of any regular expression.

The options weighed:

1. **The types of a project in `project.yml`, the profile holding those it uses.** `SemanticType`
   becomes a class of a name, a sensitivity and a detector, the types of the tool its constants;
   the profile writes the types of the project its matches name, so that it stays whole for
   `describe` and `report`. The `match` statements over the types go, as detector and sensitivity
   are fields. It costs a new format of the profile, and a type of a project has its pattern alone,
   no check, whose reading by the database shows only in `scan`.
2. **The types of a project in `project.yml` alone, the profile naming them.** A smaller profile,
   but `describe` and `report` would read the types from the project again, and a profile could not
   be read without its project, against the principle that the stages share nothing but the profile
   and the workspace.
3. **A type given by hand, by an override, without a pattern.** A label, which recognises nothing;
   of no use for a number found in many columns.

## How

As decided with the maintainer: option 1. The interface - `SemanticType`, the section of the types
in `project.yml` and the format of the profile - is put before the maintainer before it is built.

Open for that interface:

- A type of a project whose name is one of the tool is refused, naming the type.
- Its pattern is checked to compile in Python when the configuration is read; whether it uses only
  what Python and the database share, as the module docs of `detect` ask, cannot be checked there.
- The generator refuses a type of a project, naming it, as long as no profile of the simulation
  needs one.

## Done when

- The interface is agreed with the maintainer.
- A type given in `project.yml` is recognised by `scan` in the sample and verified on the whole
  table, and its sensitivity keeps the values of its columns out of the profile.
- A profile with a type of a project is read by `describe` and `report` without the project.
- `README.md` says how a project gives a type of its own.

## History

- **2026-11-02** — Opened as the maintainer asked for patterns of their own, such as `A[0-9]{10}`
  for account numbers; option 1 chosen by the maintainer.

- **2026-11-02** — The interface agreed with the maintainer. `SemanticType` becomes a frozen
  dataclass of a name, a sensitivity and a detector; the types of the tool are constants of
  `data_profiler.detect`, listed in `BUILT_IN`, and `detect` and `is_sensitive` take the types of a
  project, beside which they check those of the tool - a parameter passed on by `scan` and
  `recognise`, rather than a class that would hold no more than a list. `project.yml` gives the
  types of a project under `types`, each by its name with its pattern and its sensitivity, both
  required; `Project.read` refuses a name of the tool, a name other than of lower case letters,
  digits and `-`, and a pattern Python does not compile. The profile, of format 5, holds all types
  of the project as `types`, not only those its matches name, as said above: `disclose` checks each
  value by every type, also in `describe` and `report`. A match names its type by its name, which
  is resolved when the profile is read. In two steps, each reviewed on its own: first the type a
  class, without a change of behaviour; then the types of a project.

- **2026-11-02** — Step 1 done, without a change of behaviour: `SemanticType` is a frozen
  dataclass of a name, a sensitivity and a detector, the types of the tool are the constants of
  `data_profiler.detect`, listed in `BUILT_IN`, and `detect.semantic_type` finds one by its name.
  This undoes a decision of step 1 of [08](08-detection.md): a type no longer names its detector
  and its sensitivity by a `match` that mypy finds incomplete when a type is added, but holds them
  as fields; the generator of the simulation makes the texts of each type of the tool by a table,
  and a test that it has one for every type takes the place of mypy. The profile writes a type by
  its name and resolves it when it is read, refusing an unknown name with the message pydantic gave
  for the enumeration. `pydantic-core`, whose error that message is raised by, is named among the
  dependencies, as every package imported is.

- **2026-11-02** — Step 2 done: `project.yml` gives the types of a project under `types`, each by
  its name with its pattern and its sensitivity; `detect.project_type` makes one, refusing a name of
  the tool, a name other than of lower case letters, digits and `-`, and a pattern Python does not
  compile, by `SemanticTypeError`; `detect.all_types` names the types the values of a project are
  checked for, those of the tool and its own. `detect`, `is_sensitive` and `semantic_type` take the
  types of the project, which `scan` passes to `recognise` and `disclose` and writes into the
  profile, of format 5, in the form of `project.yml`; `Overrides.laid_over` discloses by the types
  of the profile. As the maintainer chose, the names of the matches are resolved by a context of
  the validation: `read_document` gives each document a context of its own, into which the profile
  reads its types before its fields are checked; the field `types` checks them again, and refuses
  them naming the field. The generator of the simulation refuses a match of a type of a project.
  Differing from the interface agreed: the format of `project.yml` is raised to 2, as its version is
  raised with every field added, as that of the profile is; and the form of the types in a
  document, `profile.SemanticTypes`, lives with the profile, which is read without its project,
  and `project` reads its types by it. A pattern is checked by Python alone; whether the database
  reads it shows only in `scan`.

- **2026-11-02** — Done, as the maintainer accepted step 2 and decided: a `project.yml` of format 1
  is refused as an older profile is, though it would read as one of format 2 without types; the
  types are read twice for the context of the validation, as chosen. The documentation of
  `profile.FORMAT`, which left open whether older formats are read again, now says that they are
  refused, and a profile is scanned again.
