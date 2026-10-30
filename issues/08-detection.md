# 08 — Detection

**Status:** in progress
**Type:** feature
**Priority:** high
**Area:** Detection
**Epic:** [02](02-first-version-epic.md)
**Summary:** Nothing recognises what the values of a column are - phone numbers, postal codes, IBANs, card numbers, dates -, nor whether they are sensitive.

## The problem

Detectors decide what a column is (`docs/ARCHITECTURE.md`, "Detectors decide, the language model
names"): each recognises one semantic type, precisely in the values of a sample and, where it can,
on the whole table by a pattern in SQL; what it finds is a match, with the share of values that
match. Each semantic type has a sensitivity - personal data under GDPR, payment card data under PCI,
or none -, by which the profile is kept free of sensitive values.

## Why it matters

The matches are what the language model of [10](10-the-stage-describe.md) names columns from, and
the sensitivity is what lets raw values into the profile at all ([07](07-the-stage-scan.md) keeps
them out until this issue).

## What is to be decided

The interface first, put before the maintainer: `SemanticType`, `Sensitivity`, `Detector` and
`Match`.

- **The first detectors.** Recommendation: e-mail address, phone number (`phonenumbers`), German
  postal code, IBAN and card number (checksums by `python-stdnum`), date and time in a text
  column. Names of persons and addresses are hard to recognise deterministically; they are weighed
  separately - by lists of names, or left to the language model as a guess, marked as one.
- **When a column is of a type.** The share of matching values that makes a match - one share for
  all detectors, or one each.
- **Verifying on the whole table.** The share of matching values over all rows by the pattern in
  SQL, for the types found in the sample; a detector without a pattern says that its match rests
  on the sample alone.
- **Raw values into the profile.** The values of enumerations and the ranges of columns of no
  sensitivity move from the workspace into the profile; a column no detector recognises counts as of
  no sensitivity, and the range of a text is never written.
- **The generator.** [05](05-the-simulation-environment.md) learns to generate values of each
  semantic type, so that the round trip of [07](07-the-stage-scan.md) covers the detectors.

## How

As decided with the maintainer:

- **Sensitivity is judged optimistically.** The profile and the report hold no sample, so a column
  is sensitive only where a detector recognises a sensitive type in it; in doubt it is not, and a
  user marks it by an override ([11](11-overrides.md)). A postal code is of no sensitivity; names,
  which no detector recognises yet, are none until marked.
- **More hypotheses rather than fewer.** Every column is checked, whatever its type, its values as
  text; the range of a column - its smallest and largest value - is counted for texts too, which
  hold numbers with a prefix of letters at times. Every semantic type that one value of the sample
  matches is verified on the whole table, by the detector's pattern; a type that half of the
  values of the sample match, or more, is a match of the column.
- **The interface:** `Sensitivity` and `SemanticType` - each type with its sensitivity -,
  `Detector` - a type, a check of a value, and a pattern in SQL or none - and `detect`, the types
  of the values of a sample, in `data_profiler.detect`; `Match` - a type with its share in the
  sample and on the whole table - in the profile; a building block `matching` of the dialect, which
  counts the values a pattern matches.

In steps, each reviewed and committed on its own:

1. `data_profiler.detect`: the semantic types, their sensitivity, the detectors and `detect`.
2. The matches in the profile, of a new format, found by `scan` in the samples.
3. The matches verified on the whole table, by the patterns of the detectors.
4. The generator makes values of each semantic type, so that the round trip covers the detectors.
5. The values of enumerations and the ranges of columns of no sensitivity in the profile.

## Done when

- The interface is agreed with the maintainer.
- Every detector is tested on values that match and values that do not.
- In the round trip, the semantic types of the generated profile are found again, verified on the
  whole table where the detector has a pattern.
- No value of a sensitive column is in the profile.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-30** — The interface and the steps put before the maintainer, who decided that
  sensitivity is judged optimistically, with overrides to mark what is missed, and that more
  hypotheses are checked rather than fewer: every column, and the ranges of texts as well. Not
  decided by the maintainer, for the review of step 2: the share of a match, one half of the values
  of the sample, chosen low after the rule of more hypotheses; and the verification of every type
  that one value of the sample matches, not only of the matches.

- **2026-10-30** — Step 1 done: `data_profiler.detect` holds the semantic types - e-mail address,
  phone number, German postal code, IBAN, card number, and a date as text, with a time and a time
  zone or without -, each with its sensitivity and its detector, and `detect`, the share of the
  values of a sample each type is recognised in, their spaces at either end cut. Details that
  differ from the interface put before the maintainer, for the review: `detect` gives the shares by
  type, of every type one value is of, rather than matches, since the matches are made of the
  shares in the sample and on the whole table, which `detect` does not count; every detector has a
  pattern - what the check of a value is tried on first, and what verifies a type on the whole
  table -, given compiled, its text what SQL is sent, and carrying as much of the check as a
  pattern can: the digit of an issuer of a card, the months and days of a date; a detector tells by
  `recognises` whether a value is of its type; and a type names its detector, as it names its
  sensitivity, both by a `match` that mypy finds incomplete when a type is added, rather than a
  detector naming its type. A phone number begins with `+` or `0`, and a dot is no separator of
  it, so that dates and decimals, which `phonenumbers` takes for numbers that can be dialled, are
  none; a number written without its leading zero is not recognised. On the whole table, the
  share of a type with a check, which SQL does not make, is that of its pattern: at most the share
  the check would give - to be said in step 3.

- **2026-10-30** — Step 2 done: a column of the profile has its matches, each a semantic type
  with the share of the values of the sample that are of it, written by the name of the type and
  to three digits, the most frequent first; the format of the profile is 2, and the example of the
  simulation with it. The new module `data_profiler.matching` recognises the types of the
  columns of a table in its sample, beside `statistics`, `enumerations` and `sampling`, which
  `scan` calls in the same way; a type is a match where it is recognised in half of the values of
  the sample that are not null, or more. The module, which step 3 extends by the verification on
  the whole table, is a proposal of the review, for the maintainer's. A document leaves out a field
  that has its default rather than one that is None, so that a column without matches has no
  `matches: []`. The share on the whole table comes with step 3, in the same format, since no
  profile of format 2 is in `main` before then. In the simulation, every column of dates and times
  is a `date`, and `ord_itm.pos_no`, whose generated numbers are mostly of five digits, a
  `postal-code` - a hypothesis, as the maintainer wants them.

- **2026-10-30** — Step 3 done. As the maintainer agreed with step 2, the share in the sample, of
  the precise check, decides what a match is and in which order, and the share on the whole table is
  told beside it: SQL tries only the pattern, so that the share on the table of a type whose
  detector checks more - a phone number, an IBAN, a card number, a date - is at least the one its
  check would give. A match has its share on the table, `table`, of the values that are not null;
  the dialect counts the values a pattern matches whole by the building block `matching`, each as
  text with its spaces cut, a value that cannot be cast to text matching nothing, and
  `data_profiler.matching.verify` asks for all matches of a table in one query, with the values of
  each column that are not null, so that a table written to in between gives no share above 1, and
  sends none where the table has no match. One detail differs from what How says, for the
  maintainer's review: only the matches are verified, not every type one value of the sample is of,
  since a type under the share of a match in the sample is no match, whatever the table says, and
  nothing would show its share. A test sends the pattern of every type to Trino, which reads them
  all; that they find there what they find in Python, the round trip of step 4 shows.

- **2026-10-30** — Step 4 done: the generator makes the texts of a column with a match as values of
  its first semantic type, of the lengths of its statistics, and keeps only those its detector
  recognises - German phone numbers of Berlin, Hamburg and Munich, e-mail addresses, postal codes,
  German IBANs with their check digits, alone or in groups of four, card numbers of Visa and
  Mastercard with theirs, dates as text in ISO or German form; a length no value of the type has is
  refused, naming the column. The shares of a match are not made: all values of such a column are of
  its type. `simulation` names `python-stdnum` among its dependencies, which it imports. The example
  of the simulation has the match of each of its five columns of such a type, and the round trip
  finds each of them again, in the sample and on the whole table, with all their values: the
  patterns find in Trino what they find in Python.
