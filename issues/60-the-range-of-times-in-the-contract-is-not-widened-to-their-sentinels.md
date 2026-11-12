# 60 — The range of times in the contract is not widened to their sentinels

**Status:** in progress
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

2026-11-12: Widened, with the maintainer, by what the analysis found in the simulation:

- **Two forms of a value.** The range, the values of enumerations and the samples are read of the
  database uncast and written as Python writes them (`values.as_text`), the sentinels as the
  database casts them: `08:00:00` beside `00:00:00.000`, `-1.0` beside `-1.0E0`. Python rounds a
  time of more than six digits, `.123456789` to `.123457`, so that the range of the profile can be
  broken by the row it is of; and `detect.is_sentinel` finds in a sample no sentinel of a `double`
  or a `time` that the database counts.
- **Moments.** A sentinel of a `timestamp` is a day, as the database compares a moment with it:
  the bound it widens the maximum to, `9999-12-31`, is broken by the rows of that day.
- **Zones.** Of a `timestamp with time zone`, the day of a value is its day in its own zone, so
  that a bound of no zone may be broken by up to fourteen hours; Trino orders a
  `time with time zone` by its time of day in UTC, modulo a day, which neither the texts nor
  Python's `time` do.

Decided: a step before the others, without an issue of its own, makes the database's form the one
form of a value: every value read of the database is read as the text the dialect casts it to - but
of a type it writes no text of, an array, a map, a row, a binary, which stay as they are -, and the
dialect, not `detect`, tells whether a value of a sample is a sentinel, a moment by its day. Then
times of no zone are widened to every sentinel found but numbers that are not finite. Last, a day
of a moment widens its bounds to the first and the last moment of the day, of the precision of the
type, which the dialect tells - of a zoned type at the extreme offsets, `+14:00` and `-14:00` -,
and the contract compares zoned times as Trino orders them. Rejected: an `exclusiveMaximum` of the
day after, which `9999-12-31` has none of; leaving out the bound a sentinel lies beyond, which
hides the sentinel from the contract altogether, the most frequent one, `9999-12-31`, first.

2026-11-12: The step before the others done: the dialect reads every value as the text it casts it
to, `Dialect.text` - the ends of a range, the values of an enumeration, of a sample and of the
discriminators -, and tells whether a value read is a sentinel, `Dialect.is_filled`, in place of
`detect.is_sentinel` and `detect.is_filled`; `values.as_text` is gone. The dialect compares a value
with the sentinels as it reads it, by one expression: a JSON scalar of no quotes, an array, an
object and `null` as JSON - so that a JSON `null` is the sentinel `null` now, which the database
did not count before -; a `char` of no padding, as Trino casts it. A sample of an earlier version,
which `describe` reads, holds the values as Python wrote them, until the table is scanned anew.
With the maintainer, from the review: `Dialect.matching` takes the type of the values, and matches
them as `text` reads them, as a detector sees them; `Source.grouped` gives each group the name of
its column, not its place; the module `values`, which holds counts alone, is `counts`. The filter of
the values of a sample by `Dialect.is_filled` stays at its callers, as no part owns the column of a
sample, and the tests make their dialect by its URL, as they did.

2026-11-12: Step 1 done: the bounds of a column in the contract are widened to every sentinel found
but a number that is not finite, `_is_of` is gone, so that those of times are widened as those of
numbers and days are. A time of a zone is widened as its text orders, until the next step orders it
as Trino does: leaving it out, as decided above, would have been a case of its own that the next
step removes again. The maximum of a moment is still the day of its sentinel. With the maintainer,
from the review: a number that is not finite, of the range or of the sentinels found, leaves out
the bound it would be - `Infinity` the maximum, `-Infinity` the minimum, `NaN` both -, as its rows
would break it; a range up to `Infinity` with a sentinel found made the export fail before.
