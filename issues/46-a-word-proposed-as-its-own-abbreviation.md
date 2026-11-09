# 46 — A word proposed as its own abbreviation

**Status:** done
**Type:** bug
**Priority:** low
**Area:** Describe
**Summary:** `describe` records a term written out as an abbreviation of the concept of the same word, `iban: [iban]`, though the abbreviations of a concept are the terms it is written as beside its word.

## The problem

Where the language model proposes the concept of a term, `describe` makes it `Concept((term,), ...)`
whatever the word proposed is. For a term written out, `iban` or `status`, the word is the term, so
that the glossary of the profile holds the word once more as its abbreviation. `Concept` says of
its abbreviations that they are the terms it is written as beside its word, and that a word of one
term is a term of it already.

## Why it matters

Little goes wrong: `Glossary` takes each term once. The report shows the word in the column of the
abbreviations, however, and each reader of a glossary has to allow for an abbreviation that is
none. `Overrides.adoptable` of `adopt`
([44](44-merging-the-glossary-proposed-into-the-overrides.md)) does not offer it, by the same
comparison with `written_as` that leaves out the abbreviations given; it needs no change either way,
and has to cope with the profiles already written.

## Considerations

- **The term is left out where it is the word**, so that such a concept has no abbreviations.
  Recommended, by comparing with `written_as`, not by a second rule.
- **It changes what `_laid_over` does with such a concept.** One whose abbreviations a concept given
  has all taken is dropped; one without abbreviations is kept. Given `account: [iban]`, a proposed
  `iban: [iban]` is dropped today, while a proposed `iban` without abbreviations would be kept, and
  the term stand for either. `docs/PROJECT.md` says both that a term given stands for the concepts
  given alone, and that a term that is the word of another concept stays a term of that concept.
  Which is wanted here is to be decided, and tested.
- **Profiles already written** keep such abbreviations until `describe --anew`; nothing refuses
  them, so that no migration is needed. Whether the format of the profile is raised is to be judged
  by the rules of `documents`.

## Done when

- A concept proposed of a term that is its word has no abbreviations in the profile, and a test of
  `describe` shows it.
- The case of a term given as an abbreviation of another concept behaves as decided, and is tested.

## History

- **2026-11-09** — Opened, as the maintainer asked, from a finding of the work on
  [44](44-merging-the-glossary-proposed-into-the-overrides.md).

- **2026-11-09** — Done: a concept proposed of a term that is its word has no abbreviations. Given
  `account: [iban]`, a concept `iban` of no abbreviations is dropped, as `iban: [iban]` is: a
  concept proposed goes once its abbreviations are all taken, or its word where it has none. It
  would else have left the term standing for either and had `adopt` offer its description. The same
  holds of a concept that `describe` left without abbreviations as no name has them any longer. The
  format of the profile stays as it is, the meaning of its field unchanged. A word the glossary has
  still takes the term as an abbreviation, its own word as well: that is only where the concept was
  dropped for an abbreviation given and a name has its word, and the abbreviation is what keeps it,
  as the language model would else be asked of the term at every run.
