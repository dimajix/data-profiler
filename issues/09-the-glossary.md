# 09 — The glossary

**Status:** open
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
