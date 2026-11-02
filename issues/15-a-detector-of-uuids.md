# 15 — A detector of UUIDs

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of UUIDs written as text, so that a key of that kind is told to the language model as nothing but a text.

## The problem

The detectors of [08](08-detection.md) recognise e-mail addresses, phone numbers, postal codes,
IBANs, card numbers and dates. Keys and references are often UUIDs, held in a column of `varchar`
or of the type `uuid` of Trino; no detector recognises them, so that the matches of such a column
say nothing about what it is.

## Why it matters

The matches are what the language model of [10](10-the-stage-describe.md) names columns from; a
column recognised as one of UUIDs is a key or a reference, which helps to name it.

## What is to be decided

- **The sensitivity.** None, as an identifier of a thing - in line with sensitivity judged
  optimistically, an override marking the column that holds the key of a person -, or personal
  data, as a pseudonym of one, which would make nearly every key sensitive.
- **The forms.** The form of text of RFC 9562 alone - 32 hexadecimal digits in groups of 8, 4, 4,
  4 and 12, joined by hyphens -, or also the 32 digits without hyphens, which hashes such as MD5
  have as well, and the GUID of Microsoft in braces.
- **The simulation.** A column of UUIDs in the example profile, so that the round trip covers the
  detector.

## How

As decided with the maintainer:

- **No sensitivity.** A UUID is of the sensitivity none; an override marks a column that is
  sensitive all the same.
- **The form of RFC 9562 alone**, in upper or lower case, its version and variant not checked;
  the pattern alone decides, as for a postal code.
- **A column of UUIDs in the example of the simulation**, which the generator fills and the round
  trip finds again.

## Done when

- The detector is tested on values that match and values that do not.
- In the round trip, the column of UUIDs of the example is found again, in the sample and on the
  whole table.

## History

- **2026-11-02** — Opened as the maintainer asked for a detector of UUIDs, with the sensitivity,
  the forms and the column of the simulation decided.

- **2026-11-02** — Made as decided: the semantic type `uuid`, of the sensitivity none, recognised
  by its pattern alone - 32 hexadecimal digits in groups of 8, 4, 4, 4 and 12, in upper or lower
  case, their version and variant not checked -; the generator makes random UUIDs of version 4,
  and the example of the simulation has the column `ord.pymt_ref_id` of them. The round trip and
  the test that sends every pattern to Trino were not run where the change was made, which has no
  simulation environment; the issue is done once they pass.

- **2026-11-02** — Done: the maintainer ran the tests with the simulation environment, the round
  trip and the test that sends every pattern to Trino among them, and all of them passed; the
  column `ord.pymt_ref_id` is found again, in the sample and on the whole table.
