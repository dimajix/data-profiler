# 60 — The range of times in the contract is not widened to their sentinels

**Status:** open
**Type:** bug
**Priority:** low
**Area:** Export
**Summary:** The data contract widens the range of a column to the sentinels found in it, which the range is counted without, but not that of a column of the logical type `time`, so that its rule of minimum and maximum fails on rows it was observed of.

## The problem

The contract of [57](57-export-as-open-data-contract.md) writes the range of a column as the bounds
of its values, `minimum` and `maximum` of `logicalTypeOptions`, widened to the sentinels found in
it: the range is counted without them, and the contract holds of the rows it was observed of, the
sentinels taken as values, so that the experts see them to forbid.

`_bounds` in `src/data_profiler/contract.py` (around line 251) widens them only by the sentinels
that `_is_of(text, logical)` takes as values of the logical type: numbers, and days of a `date` or
a `timestamp`. `time` is among the logical types whose range the contract writes, `_RANGED`, but
`_is_of(text, "time")` is False. A sentinel given of a column of times and found in it - such as
`00:00:00.000` - does not widen its bounds: a column of times from `08:00:00.000` to
`18:00:00.000` with rows of `00:00:00.000` gets the minimum `08:00:00.000`, which those rows break.

## Why it matters

The contract is to be an inventory of what was observed: every rule it writes holds of every row
the profile was counted of. A rule that the observed rows break is wrong where an expert would trust
it most, as it was generated, not written.

## Considerations

**What `_is_of` filters out at all.** The sentinels found were found by comparing the text the
database casts a value to, so that they are of the form of the values of their type already - the
dialect's `held` keeps no others since
[58](58-the-configuration-of-a-project-its-class-and-its-examples.md). Of a number, `_is_of` leaves
out only those that are no finite numbers, `NaN` and `Infinity`, which cannot be compared with the
bounds; of a day, it leaves out nothing.

- **Filter only what cannot be compared**: take every sentinel found of a column of a range, but
  the numbers that are not finite. Times, days and moments compare as their texts, as the range of
  the profile is of texts too. This removes a check that only repeats what the scan ensured.
- **Take `time` into `_is_of`**: the smallest change, but it keeps a filter whose other cases say
  nothing.

The first is preferred. To check: whether a time of another precision or zone than the range - a
sentinel `00:00:00` of a `time(3)` cannot be found, as Trino writes `00:00:00.000` - can reach the
bounds at all.

## Done when

The bounds of a column of times in the contract are widened to the sentinels found in it, as those
of numbers and days are, with a test of it.

## History

2026-11-12: Opened on the maintainer's request, from a finding of the review of step 2 of
[58](58-the-configuration-of-a-project-its-class-and-its-examples.md); the fault is older, of 57.
