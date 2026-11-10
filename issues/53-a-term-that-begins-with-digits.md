# 53 — A term that begins with digits is cut in two

**Status:** done
**Type:** bug
**Priority:** medium
**Area:** Describe
**Summary:** A name is cut inside `3rd`, into `3` and `rd`, and a concept of `3rd` is never found.

## The problem

`terms` in `glossary.py` cuts a name between letters and digits in both directions, which is right
for `addr2`, into `addr` and `2`, but takes `3rd` apart:

| name | terms today |
|---|---|
| `3rd_party` | `3`, `rd`, `party` |
| `party_3rd` | `party`, `3`, `rd` |
| `2ndAddr` | `2`, `nd`, `addr` |
| `addr2line` | `addr`, `2`, `line` |
| `b2b_flag` | `b`, `2`, `b`, `flag` |
| `sales_30d` | `sales`, `30`, `d` |

A term of digits needs no concept and stands for itself, so that what is left to name is `rd`: it
is what `occurrences` lists and what the language model is asked about, though it means nothing
without its digit.

Giving `3rd` as an abbreviation of `third` in the overrides does not help. The cut is made in
`terms`, before the vocabulary is consulted; `Vocabulary._split` only ever sees `3` and `rd`, and
`Glossary.words` is never asked for `3rd`. The module documentation promises otherwise: "A term a
concept is written as is never split, so that a person stops a wrong split by giving the term a
concept." That holds for terms written together ([24](24-terms-written-together.md)), not for the
cut at digits. The same goes for the word of a concept: `written_as("3rd", ...)` takes it for two
terms, and `snake_case("3rd")` gives `3_rd`.

## Why it matters

Ordinals are common in names of addresses, parties and contacts. Each `rd`, `nd` and `st` becomes a
term of the glossary of its own, whose concept can only be guessed, and a person who sees the wrong
guess has no way of correcting it: the correction the overrides offer has no effect.

## Considerations

A *part* below is what is left between separators, before case and digits are looked at.

- **Digits always join the letters after them.** `3rd` stays whole. But where digits follow letters
  they mostly belong to what is before them or stand alone: `addr2line` gives `addr` and `2line`,
  `b2b` gives `b` and `2b`. `2line` is a new term that no concept can cut again, the problem of this
  issue the other way round.
- **Digits at the beginning of a part stay with the letters after them.** `3rd_party`, `party_3rd`
  and `2ndAddr` give `3rd`, while digits after letters are cut as before: `addr2line` and `b2b` stay
  as they are. One condition in `_splits`, and as it is in `terms`, words and `snake_case` agree.
  The cost: `sales_7d` and `sales_30d` become terms `7d` and `30d`, each needing a concept of its
  own, where the one concept of `d` served all of them today.
- **Only single digits do so.** Keeps `30d` apart but not `7d`, so that two columns of one pattern
  would be split differently, and misses `21st`. Not recommended.
- **Only ordinals are kept whole**, digits followed by `st`, `nd`, `rd` or `th` and no other letter.
  Keeps `30d` apart, but it is a list of English suffixes in a tool whose names are often in other
  languages, `2te`, and it leaves `3d` and `2fa` in pieces.
- **A concept written as a term stops the cut at digits**, which makes the promise of the module
  documentation true. It also serves `b2b`, `addr2line` and `address3rd`, which no rule by position
  can tell from each other. It needs `Vocabulary.split` to see the parts, as `terms` loses the
  difference between `3rd` and `3_rd`. On its own it leaves `rd` as what the language model is asked
  first, until a person has noticed and given `3rd`.

**Proposal, to be decided:** digits at the beginning of a part stay with the letters after them.
It repairs the case reported with the least machinery, and the override works then, since `3rd` is
a term. A concept stopping the cut at digits comes on top only if names like `b2b` turn out to
matter; if it does not, the sentence of the module documentation is to say that it holds of terms
written together.

Whatever is chosen changes the terms of the names concerned. `describe` keeps a reading only while
the terms of its name are unchanged, so that these names are read again; the format of the profile
does not change. Concepts of `rd` or `nd` given in overrides simply find no term any longer, which
[30](30-abbreviations-given-that-no-name-has.md) allows.

## What is decided

As the maintainer decided, instead of the proposal above:

- **No rule by position.** Names are cut as before, and the cuts are candidates.
- **A term a concept is written as is found across those cuts**: parts of a name, one after the
  other, that are the pieces of such a term are that one term, the fewest terms being taken.
  `3rd`, `b2b` and `contract_item` are found so, once a concept is written as them.
- **The word of a concept is a term of it, of several terms as well**, so that `contract_item: {}`
  is enough. That changes what [29](29-the-word-of-a-concept-as-a-term.md) decided, where a word of
  several terms was written as its abbreviations alone.
- **All concepts count**, those proposed as well as those given, as in the vocabulary already.
- **A word is not cut at digits**: `snake_case` cuts it as a name is cut but between letters and
  digits, so that `b2b: {}` is the term `b2b` and makes the name `b2b_flag`, and `Address2` is
  `address2`. A term of digits still stands apart in a harmonized name, `address_2` of `addr2`.

## Done when

- The names above are split as decided, and `test_a_name_is_split_into_its_terms` shows it, the
  names whose split must not change included.
- A concept with the abbreviation `3rd` is found for `3rd_party`, and the harmonized name is
  composed of its word, `third_party`.
- The documentation of `glossary.py` says how digits are treated, and promises nothing that does
  not hold.

## History

- **2026-11-10** — Opened, as the maintainer asked, with the question whether digits should join
  the term after them or something else keeps such terms recognisable. The decision is open.

- **2026-11-10** — Decided by the maintainer, as under "What is decided": terms of the concepts are
  found across the cuts of a name, and the word of several terms is a term.

- **2026-11-10** — Done, as decided: `Vocabulary.split` joins the pieces of a term a concept is
  written as, by the routine that splits terms written together. The pieces of such a term are not
  split either, and are not found as terms of their own, so that `rd` of `3rd` splits no `card`. As
  names are cut as before, `test_a_name_is_split_into_its_terms` did not change; the tests of the
  decision are `test_a_term_a_concept_is_written_as_is_found_across_the_cuts_of_a_name` and those
  after it. The format of the profile is unchanged: no field changed, and a profile is split anew
  by `describe`.

- **2026-11-10** — As the maintainer decided on seeing `b_2_b_flag`: `snake_case` no longer cuts at
  digits. A name given by hand may therefore hold digits among its letters, `address2`, which an
  older tool refuses, so that the minor version of the format of the overrides is raised. A word
  a profile already holds as `b_2_b` stays as it is until a concept given of `b2b`, which takes its
  place, or `describe --anew`. That terms are cut and words composed otherwise was not taken for a
  change of the meaning of a field, as in [24](24-terms-written-together.md).
