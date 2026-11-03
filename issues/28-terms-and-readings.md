# 28 — Terms and readings

**Status:** open
**Type:** feature
**Priority:** high
**Area:** Describe
**Epic:** [02](02-first-version-epic.md)
**Summary:** The terms of a name are computed whenever they are needed, and which concept a term of several stands for is said nowhere, so that the split of a name changes unseen with the profile, a name of a term repeated in two meanings cannot be read, and a scan would lose what was found of the names.

## The problem

The terms of a name are not held in the profile; they are computed from it whenever a stage needs
them ([09](09-the-glossary.md)). Once terms written together are split by the vocabulary of the
whole profile ([24](24-terms-written-together.md)), the split of a name follows from every table
and from the glossary: a new table, or a concept given, changes it, and no one sees that it did.
An abbreviation may be of several concepts ([27](27-glossary-of-concepts.md)), and nothing says
which one a term of a name stands for - in `ap_ap_nm`, a custom column of the name of a contact
person, `ap` is AirPlus first and a contact person second. And `scan`, counting a table anew,
replaces the whole table in the profile, whatever another stage found of it.

## Why it matters

The split of the names along the glossary is a result of its own, before a language model makes
names and descriptions of it: a person checks it, and the language model is shown the terms of
each name with their concepts. A harmonized name is only as good as the reading of each term it
is composed from.

## What is decided

As discussed with the maintainer:

- **The principle.** Every attribute of the profile is filled by exactly one step, and a step
  replaces in a profile there is the attributes it fills alone, keeping all others. It goes into
  the principles of `docs/ARCHITECTURE.md`.
- **The terms** of the name of a table or column, filled by a step of `describe` of its own, that
  splits the names along the vocabulary ([24](24-terms-written-together.md)), without a language
  model: each term in the order of the name, with the concepts it is an abbreviation of, its
  candidates.
- **The reading** of the name, filled by the next step of `describe`: exactly one concept for each
  term, at the same place as in the terms. Where every term has one candidate, the reading
  follows; where a term has several, the language model chooses ([10](10-the-stage-describe.md)),
  in the same step, and until it does, the name has no reading. An override gives the reading of a
  table or column in place of the one read.
- **Harmonized names** are composed from the reading alone, without the concepts omitted; a name of
  no reading has none.
- **A reading that no longer agrees** with the terms - of another length, or a concept that is no
  candidate of its term, as an interrupted `describe` may leave it - is kept, but read as none,
  and read anew by the step that fills it; the profile is not refused for it.
- **Candidates are what the glossary had** when the terms were split: a concept given later counts
  once `describe` splits the names again, as sentinels changed count once `scan` counts again.
- **The steps of `describe`**, once [10](10-the-stage-describe.md) adds those of the language
  model: split the names; propose concepts of the terms of none; split again, so that they are
  candidates; read the names; propose names and descriptions. Until then, it splits and reads.
- **`scan` keeps** the terms and readings of every table and column whose name stays, as every
  other attribute it does not fill. A scan with other semantic types keeps the tables, and drops
  their matches alone, counting the tables anew, in place of dropping the tables.
- **A wrong split** is corrected by the glossary: a term of a concept is never split.

## What is to be decided

The interface first, put before the maintainer.

- **The types.** The class of a term with its candidates, the reading, where both are held, and
  the format of the profile and of the overrides, both raised.
- **Which attributes each step fills**, named in one place, and how `Profile.updated` keeps those of
  the others.
- **The command line.** `describe` on an environment, its steps, and whether one can be run alone.
- **The report.** Harmonized names from the readings; whether it shows the terms with their
  candidates, and the names without a reading.

## Done when

- The interface is agreed with the maintainer.
- `describe` splits and reads the names of a profile of the simulation environment, and writes
  their terms and readings, which a scan of it afterwards keeps.
- The example has a name of a term of two concepts, read by an override, and one of a term
  repeated in two meanings.
- Harmonized names are composed from the readings, and the report shows them.

## History

- **2026-11-03** — Opened while [27](27-glossary-of-concepts.md) was planned, as the maintainer
  decided: the meanings of the terms of a name, which 27 was to hold term by term, became the
  terms and the reading of the name, each filled by a step of its own, and every step keeps what
  the others found.
