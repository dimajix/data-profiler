# 20 — Detectors of boolean pairs

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of flags written as `true`/`false`, `yes`/`no` or `0`/`1`, so that a flag is told to the language model as nothing but a text or a number.

## The problem

The detectors of [08](08-detection.md), [15](15-a-detector-of-uuids.md) and the types of a
project of [16](16-semantic-types-of-a-project.md) recognise e-mail addresses, phone numbers,
postal codes, IBANs, card numbers, dates and UUIDs. Flags are among the most frequent columns of a
database, and are written in one of a few pairs of values: `true` and `false`, `yes` and `no`, `0`
and `1`. No detector recognises them; a column of flags is at most an enumeration of two values,
and only where its values are disclosed.

## Why it matters

The matches are what the language model of [10](10-the-stage-describe.md) names columns from; a
column recognised as a flag is named as one - `is_…`, `has_…` -, and the report shows it as one.

## What is to be decided

Three detectors, one for each pair, as the maintainer asked: three semantic types of the tool, so
that a match says which pair a column is written in, and a column that mixes the pairs is no match
of any of them.

- **The names of the types.** For instance `true-false`, `yes-no` and `zero-one`, or a common
  prefix, `boolean-true-false`, … .
- **The sensitivity.** None, as of a postal code or a UUID.
- **Upper and lower case.** The patterns are shared by Python and SQL, which share no flag that
  ignores case; the cases are written out - `true`, `True`, `TRUE` -, or in classes of a letter.
  A column of the type `boolean` of Trino is read as `true` and `false` by `try_cast` on the
  table, and its sample may hold the values as Python writes them, `True` and `False`; both are to
  be recognised alike, or a column of booleans is to be no match at all - in which case the
  detector has to tell it from a column of text.
- **The forms of each pair.** Whether `yes`/`no` also takes `y`/`n`, and the German `ja`/`nein`
  and `j`/`n`; whether `true`/`false` also takes `t`/`f`; whether `0`/`1` also takes `0.0`/`1.0`
  and whatever else a column of decimals is written as.
- **A value is not a pair.** A detector sees each value on its own, and a type is a match where
  half of the values of the sample or more are of it. A column of counts, mostly `0` and `1` and
  now and then more, is then a match of `0`/`1`; so is a column of `yes` alone. The options:
  1. **The pattern alone**, as for every type now: more hypotheses are better than fewer
     (`matching.py`), and the share on the table tells a column of flags, whose share is 1, from
     one of counts, whose share is below.
  2. **A share of the whole column**, the types of a pair being a match only where every value
     that is not null is of them. It costs a threshold of its own for some types, against the one
     threshold of `matching.py`.
  3. **The number of distinct values**, at most two, from the statistics of the column. It costs
     a check of a column beside the check of a value, which no detector has yet.
- **The simulation.** A column of each pair in the example of the simulation, which the generator
  fills and the round trip finds again.

## Done when

- Each of the three detectors is tested on values that match and values that do not.
- In the round trip, the column of each pair of the example is found again, in the sample and on
  the whole table.

## History

- **2026-11-02** — Opened as the maintainer asked for three detectors of boolean pairs:
  `true`/`false`, `yes`/`no` and `0`/`1`.

- **2026-11-02** — Decided with the maintainer: the condition of a column and the threshold of a
  type, which options 2 and 3 of a value not being a pair need, become one concept for this issue
  and [21](21-a-detector-of-free-text.md), built before either as the refactoring of
  [22](22-a-condition-of-a-column.md). Which of the options the pairs take is still to be decided.

- **2026-11-02** — Decided with the maintainer: the types are named `true-false`, `yes-no` and
  `zero-one`, of the sensitivity none; each takes its pair alone, `true` and `false`, `yes` and
  `no`, `0` and `1`, the words in lower case, with a capital and in capitals, and no other forms
  (`y`/`n`, `ja`/`nein`, `t`/`f`). A column is of a pair where every value of it that is not null
  is - option 2, by a threshold of 1 -, without a condition of the column. A column of the type
  `boolean` is recognised as `true-false`, as a column of the type `date` is as a date: a detector
  sees each value as text, whatever the type of its column.

- **2026-11-02** — Made as decided: the semantic types `true-false`, `yes-no` and `zero-one`, each
  recognised by a pattern of its pair alone and the threshold 1 of its detector, so that a column
  of counts, of zeros and ones mostly, is none. The condition of a column of
  [22](22-a-condition-of-a-column.md), given all texts and those recognised for the sake of this
  issue, is not needed by the pairs as decided; its user is the free text of
  [21](21-a-detector-of-free-text.md). The generator makes a word of a pair in a case at random,
  and the example of the simulation has its two columns of the type `boolean`, `cust.actv_flg` and
  `prod.dscntd_flg`, recognised as `true-false` - read as `True` and `False` in the sample, as
  `true` and `false` on the table -, the column `cust.nwslttr_flg` of `yes-no` and the column
  `prod.rtrn_ind` of `zero-one`, which the round trip finds again, in the sample and on the whole
  table.
