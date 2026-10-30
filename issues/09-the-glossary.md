# 09 — The glossary

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Describe
**Epic:** [02](02-first-version-epic.md)
**Summary:** The original names are not split into their terms, so nothing can give a term one word for the whole database and compose harmonized names from it.

## The problem

Harmonized names are composed from the glossary (`docs/ARCHITECTURE.md`, "One word per term"): each
term of the original names - mostly an abbreviation, `CUST` in `CUST_CRT_DT` - stands for one word
in the whole database, and the name of a column is composed from the words of its terms. Neither the
splitting nor the composing exists.

## Why it matters

It is the half of naming that needs no language model, and can be tested on its own. It is also what
makes the names harmonized: one correction of a term's word corrects every column that has the term.

## What is to be decided

The interface first, put before the maintainer.

- **Splitting.** By underscores, by changes of case, by digits; whether a term that appears once
  is a term at all.
- **What the glossary holds.** Each term with the columns it appears in, which
  [10](10-the-stage-describe.md) shows the language model, and its word, once proposed or given.
- **Composing.** The harmonized name of a column from the words of its terms, in English, in
  `snake_case`; what happens to a term without a word yet.
- **Where it lives.** The glossary is part of the profile ([03](03-the-profile.md)); the profile's
  schema grows by it.

## Done when

- The interface is agreed with the maintainer.
- The terms of the example profile of [05](05-the-simulation-environment.md) are found, each with
  its columns, and names are composed from words given in a test.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-30** — Done in one step, as agreed with the maintainer. `data_profiler.glossary` splits
  an original name into its terms - at everything that is no letter and no digit, at changes of
  case, between letters and digits -, in lower case, a term that appears once included; the names
  of tables are split as those of columns are, into the same glossary. `occurrences` finds each
  term of a profile with the tables and columns it appears in, computed whenever it is needed
  rather than held in the profile; the profile, of format 3, holds the glossary alone, each term
  with its word. `harmonized` composes the name of a table or a column from the words of its terms
  in `snake_case`, a term of digits standing for itself, and composes none while a term has no
  word, rather than letting an abbreviation through. Where the suggestions of the columns are kept
  is left to [10](10-the-stage-describe.md).
  After the review: a word is split as a name is, so that `dateOfBirth` and `date of birth` both
  give `date_of_birth`, and a word of neither letters nor digits is none; `occurrences` leaves out
  the terms of digits, which need no word; a name is composed to NFC before it is split. One detail
  differs from the interface agreed, for the maintainer's review: the glossary of the profile is a
  `Mapping`, not a `dict`, as every collection of the frozen classes of the profile is immutable.
