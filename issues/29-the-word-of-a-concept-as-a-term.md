# 29 — The word of a concept as a term

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Describe
**Epic:** [02](02-first-version-epic.md)
**Summary:** A concept is written only as its abbreviations, not as its word, so that a name written in full - `name`, `customer_id` - finds no concept until its word is given once more as an abbreviation, and a concept cannot be given without abbreviations at all.

## The problem

A term of a name is a candidate of a concept only where it is one of the abbreviations of the
concept ([27](27-glossary-of-concepts.md)), and the vocabulary that splits terms written together
holds the abbreviations alone ([24](24-terms-written-together.md)). The word of a concept is
neither: a column `name` has the term `name` of no concept, though the glossary has the concept
`name`, and `customername` is not split by the concept `customer`. A person who gives the words of
a database first, before its abbreviations, cannot: the overrides refuse a concept without
abbreviations, and one with none would be the candidate of no term.

## Why it matters

Names are not only abbreviations: many are written in full, in part or whole, and a concept given
should read them without its word written again under its abbreviations. Giving the words of a
domain first is how a person begins a glossary, before the abbreviations of one database are known.

## What is decided

As the maintainer decided:

- **The word of a concept is a term of it**, beside its abbreviations, where the word is one term
  as `glossary.terms` splits it: `customer` is, `contact_person` is not, and is written as its
  abbreviations alone.
- **The abbreviations are optional** in the overrides, as the description is.
- Two steps of this issue: first the word as a term, then the abbreviations optional.

## What is to be decided

The interface first, put before the maintainer.

- **Where the terms of a concept are told.** One function of `glossary`, the terms a concept is
  written as, used wherever the terms of a concept are looked at: the candidates of a term, the
  vocabulary, and the terms the overrides take from the concepts proposed.
- **What `describe` proposes.** Whether the term it asks for stays an abbreviation of the concept
  proposed where it is the word of the concept, or is left out as written by the word already.
- **The format of the profile.** Whether it is raised with the abbreviations optional, as
  `Concept` is a class of the profile as well.

## Done when

- A term that is the word of a concept is a candidate of it, and the vocabulary splits by the
  words as by the abbreviations, an abbreviation and a word never split.
- The overrides give a concept without abbreviations and without a description.
- The example gives a concept without abbreviations: `iban`, the word of the column `iban`.

## History

- **2026-11-04** — Opened, as the maintainer decided: the word of a concept counts as a term of it,
  and its abbreviations are optional, in two steps.

- **2026-11-04** — Step 1 as agreed with the maintainer: `glossary.written_as` tells the terms a
  concept is written as - its word, where it is one term, and its abbreviations -, and the
  candidates of a term, the vocabulary and the terms the overrides take from the concepts proposed
  are of it; a word given that no name has is not refused, as an abbreviation is. `describe`
  records the term it asks for as an abbreviation, even where it is the word proposed. Beyond the
  plan, as the word counts: `describe` keeps a concept a name has the word of, without the
  abbreviations no name has, so that the profile may hold a concept without abbreviations; and
  the overrides drop a concept proposed once they take all its abbreviations, not one proposed
  without any. The word of a concept proposed is taken from it by no override, as the maintainer
  decided after the review: a term given that is the word of a concept proposed stands for either,
  as the reading of its name says, as an abbreviation of two concepts does; dropping the concept
  would leave its other abbreviations of no concept, and have the language model asked for them at
  every run of `describe`. As the profile may hold a concept without abbreviations now, its format
  is raised with step 2.
