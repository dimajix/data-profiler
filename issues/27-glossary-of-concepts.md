# 27 — Glossary of concepts

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Describe
**Epic:** [02](02-first-version-epic.md)
**Summary:** The glossary gives each term one word and nothing else, so that two abbreviations of one concept are two entries, an abbreviation of several meanings has one of them, a prefix that means nothing becomes part of every name, and the language model is told no more of a term than a word.

## The problem

The glossary of a profile is a mapping of each term to its word: `cust: customer`
([09](09-the-glossary.md)). It cannot say:

- that `cust` and `kd` are abbreviations of the same concept, which reads the same in every name;
- what a concept means, in a sentence the language model can propose names and descriptions from;
- that one abbreviation stands for several concepts, the meaning following from where it is
  written: `st` a status in `st_cd` and a street in `st_nm`, `ap` a contact person in `kd_ap_nm`;
- that a term carries almost no meaning for a name: in the first case, many columns begin with
  `ap_`, which marks a column added to the CRM for AirPlus, a custom column. It says something of
  the column, but nothing of what it holds, and is not to be part of its harmonized name.

## Why it matters

The stage `describe` ([10](10-the-stage-describe.md)) is to propose names and descriptions of the
columns from the terms of their names, through the glossary. A word alone gives the language model
little to go by; a description of each concept, and the choice between the concepts of an
abbreviation, are what lets it propose a name a person with business knowledge reads. Splitting the
terms written together ([24](24-terms-written-together.md)) needs the abbreviations of the glossary
as its vocabulary.

## What is decided

As discussed with the maintainer:

- **A concept** is an entry of the glossary: its word, the key of the entry and unique in the
  glossary, from which harmonized names are composed; its abbreviations, the terms it is written as
  in the names; and its description, a text of what it means. Descriptions are in English, as the
  suggestions are.
- **The glossary** is the concepts of a profile, proposed by `describe`, or given by the overrides,
  which come first.
- **A term** stays a part of an original name, as the names are split. It is an abbreviation of
  one concept, of several, or of none yet.
- **Several concepts of one abbreviation.** An abbreviation may be of several concepts. Which one a
  term of a name stands for is its meaning, held in `meanings` of the table or column, term by term,
  for the terms of several concepts alone: `meanings: {st: status}`. `describe` chooses it, from the
  descriptions of the concepts and what is found of the column; an override of the table or column
  gives it by hand.
- **A concept omitted.** A concept marked `omitted` is no part of a harmonized name: `ap_kd_nr`
  reads `customer_number`. It stays in the glossary with its description, which the language model
  is shown, so that a description of a column may say that it is a custom column.
- **Harmonized names** are composed of the words of the concepts of the terms, through the meanings
  where a term is of several, and none while a term has no concept, or its meaning is not chosen.
  Two columns of a table with the same harmonized name - `ap_status` and `status` - are a collision,
  shown in the report and resolved by an override, not overwritten.
- **The principle** "One word per term" of `docs/ARCHITECTURE.md` becomes "One word per concept":
  a concept reads the same in every table, and a term may stand for several.
- **No language model** is part of this issue: it changes what the glossary holds, how names are
  composed from it and what the report shows. Proposing concepts and choosing meanings is
  [10](10-the-stage-describe.md).

## What is to be decided

The interface first, put before the maintainer.

- **The types.** The class of a concept, the glossary of a profile and of the overrides, and
  `meanings` of a table and of a column; the format of the profile and of the overrides, both
  raised.
- **What is refused.** A meaning that names a word whose concept does not have the term as an
  abbreviation, a word of no concept, an abbreviation given twice in one concept; whether a concept
  given needs a description.
- **The overrides.** How a concept given lays over one proposed of the same word, and over one
  that has an abbreviation of it; how a meaning given lays over one chosen.
- **The report.** Each concept with its abbreviations, its description and where its terms
  appear; the meaning chosen of a term of several concepts; the terms of no concept; the
  collisions of harmonized names.
- **What is no longer used.** `glossary.occurrences` and `glossary.harmonized` as they are, and
  the glossary of the overrides of format 2, `cust: customer`, which a project rewrites.

## How

As agreed with the maintainer:

- **`profile.Concept`** - its abbreviations, its description, None where none is given, and
  whether it is omitted; `Profile.glossary` holds the concepts by their words. The profile is of
  format 9. An abbreviation given twice in one concept is not refused.
- **`glossary.Glossary`** - made of the concepts once, so that the words of a term are found by an
  index, not by a search of the glossary for each name: `words` of a term, `harmonized` of a name,
  and `collisions` of the columns of a table. A name of a term of several concepts has no
  harmonized name. The function `harmonized` of the module is gone.
- **The overrides**, of format 3, give concepts by their words. A concept given takes the place of
  the one proposed of its word, and its abbreviations are taken from the others, a concept left
  without any dropped. An abbreviation no name has is refused.
- **The report** shows each concept with its abbreviations and its description, and whether it is
  omitted; the terms of no concept with where they appear; and the harmonized names two columns
  of a table share.
- **The example** has a column `cust.ap_seg_cd`, whose prefix `ap` is AirPlus, omitted; its
  overrides give that concept, and an address of two abbreviations.
- **The meanings** of the terms of a name are not part of this issue (see History).

## Done when

- The interface is agreed with the maintainer.
- The profile and the overrides hold concepts with their words, abbreviations and descriptions,
  and the meanings of tables and columns.
- Harmonized names are composed through the concepts and meanings, without the concepts omitted,
  and their collisions are shown in the report.
- The overrides of `examples/crm` give a concept of two abbreviations, an omitted one, and an
  abbreviation of two concepts with the meaning of a column given.

## History

- **2026-11-03** — Opened from the plan of [24](24-terms-written-together.md), as the maintainer
  decided: the glossary is to hold concepts with their abbreviations and descriptions, so that the
  language model can propose names from them, an abbreviation may be of several concepts, its
  meaning chosen from the context, and a prefix such as `ap_` may be left out of the names. It comes
  before 24, whose vocabulary are the abbreviations of the glossary.

- **2026-11-03** — While it was implemented, the maintainer decided otherwise of the meanings of
  "What is decided": a mapping of each term of a name to its concept loses the order of the terms,
  and cannot read a term repeated in two meanings, `ap_ap_nm`. They became the terms and the
  reading of the name, each filled by a step of `describe` of its own, in
  [28](28-terms-and-readings.md), with the example of a term of two concepts; this issue holds the
  concepts alone, and a name of a term of several concepts has no harmonized name until 28.

- **2026-11-03** — Done as agreed with the maintainer (see How). The trial of
  [04](04-can-a-small-model-name-columns.md), `work/naming_trial.py`, takes the word of a term of
  one concept from the glossary, and asks for the others again. No override resolves a collision
  yet: one of the name of a column comes with [10](10-the-stage-describe.md), with the names it
  proposes.
