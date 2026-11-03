# 24 — Terms written together

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Describe
**Summary:** Terms written together without a separator, `LFADR` in `KD_LFADR_PLZ`, stay one term, so that the glossary needs a word for every combination of terms, and the same term reads differently where it is written together.

## The problem

`glossary.terms` splits an original name where something separates its terms: everything that is
no letter and no digit, a change of case, a change between letters and digits. `KD_LFADR_PLZ`
gives `kd`, `lfadr` and `plz`; nothing tells that `lfadr` is `lf` and `adr`, though `LF_DATUM` and
`ADR_ORT` in the same schema have both on their own.

## Why it matters

The glossary gives each term one word for the whole schema (`docs/ARCHITECTURE.md`, "One word per
term"). A term written together is a term of its own: it needs a word of its own, proposed apart
from those of its parts, and may get another one; a correction of `lf` does not correct `lfadr`.
It should come before or with [10](10-the-stage-describe.md), which asks the language model for the
word of every term.

## What is to be decided

The interface first, put before the maintainer.

- **The vocabulary.** The terms a term written together is split into: those found on their own,
  between separators, anywhere in the profile, and the terms of the glossary, given or proposed.
- **The split.** The one that covers the most characters by terms of the vocabulary with the
  fewest parts, by dynamic programming; a part of at least two characters; the term left whole
  where less than half of it is covered. A term of the glossary is never split, so that a person
  can stop a wrong split - `kst` as `k` and `st` - by giving `kst` a word.
- **What a split depends on.** Today the terms of a name follow from the name alone. Split by a
  vocabulary, they follow from the whole profile: a new table can change how the name of an old
  one is split, and its harmonized name. `terms` would take the vocabulary, or a second function
  would split the terms `terms` finds; `occurrences` and `harmonized` would use it alike. The
  terms stay computed whenever they are needed, not held in the profile, as decided in
  [09](09-the-glossary.md).
- **Words of terms no longer found.** A glossary that gave `lfadr` a word before keeps a word of a
  term no name has once it is split; whether it is dropped, kept or reported.
- **Terms of several meanings.** `st` may be a status, a street or a piece. A decision of its own,
  against the principle "One word per term":
  - one word per term stays, and a column whose term means something else is corrected by an
    override of its name ([11](11-overrides.md)) - simple, but every such column by hand;
  - the glossary gives a term several words, and the language model chooses the one of each column
    from what was found about it - a status of three values, a street of free text -, the
    principle changed to one word per term and meaning.

## Done when

- The interface is agreed with the maintainer, and the decision on terms of several meanings is
  recorded.
- `KD_LFADR_PLZ` is split into `kd`, `lf`, `adr` and `plz` in a profile that has `lf` and `adr` on
  their own, and left as it is where a term of the glossary covers it.
- The example profile of the simulation has a name of terms written together.

## History

- **2026-11-03** — Opened from the comparison with an earlier draft of a profile, which split the
  names by a vocabulary gained from the schema itself.
