# 08 — Detection

**Status:** open
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

## Done when

- The interface is agreed with the maintainer.
- Every detector is tested on values that match and values that do not.
- In the round trip, the semantic types of the generated profile are found again, verified on the
  whole table where the detector has a pattern.
- No value of a sensitive column is in the profile.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).
