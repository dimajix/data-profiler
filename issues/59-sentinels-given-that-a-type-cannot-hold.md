# 59 — Sentinels given that the type of their column cannot hold

**Status:** done
**Type:** bug
**Priority:** low
**Area:** Scan
**Summary:** A sentinel given of a column that its type cannot hold - `N/A` of a `bigint`, `-1` of a `double`, which Trino writes `-1.0E0` - is left aside without a word, while sentinels given of a column of no text are refused, although both are overrides that cannot be what they give.

## The problem

Since [58](58-the-configuration-of-a-project-its-class-and-its-examples.md), the dialect tells which
of the sentinels of a column its type can hold, `Dialect.held(kind, texts)`: the texts the database
casts a value of the type to, as the sentinels are compared. `statistics.count` counts those alone,
and the contract writes its rule of them. Of the sentinels given by hand, there are two cases a
column cannot hold, and they are treated differently:

- **Of a column of no text** - an array, a map, a binary -, `count` records the column as counted
  with no sentinels given, `Column.sentinels` None, and `Overrides.refuse_uncounted` refuses the
  override, naming the column.
- **Of a column of text whose type cannot hold them** - `N/A` of a `bigint`, `-1` of a `double`,
  `0.5` of a `decimal(12,2)`, which Trino writes `0.50`, a UUID in upper case -, `count` records the
  sentinels given as those it was counted with, counts the others, and leaves these aside: nothing
  is refused or warned of, and the profile names them as given.

PROJECT.md says, under "What is refused, and what is warned of": "An override that names what is
not profiled, or cannot be what it gives, is refused, naming it". A sentinel a column cannot hold
is such an override, in both cases.

## Why it matters

A person who gives `-1` as the sentinel of a column of floating numbers expects its rows to be
counted apart and left aside; the scan finds none, as Trino writes the value `-1.0E0`, and nothing
says why. Before 58, the sentinel was asked for and counted in no row, which said as little, but the
contract at least showed it in its rule; now it is not even there. The form the database writes a
value in is the one thing the person cannot see in the profile.

## Considerations

**Refuse every sentinel given that the column cannot hold, as one case.** No text is the special
case of holding none: `Dialect.held` already gives none of a column of no text.

- `count` records, of the sentinels given of a column, those its type can hold, where some are
  given - `dialect.held(kind, given)`, None where none are given -, so that `has_text` leaves
  `statistics.count` altogether and `held` is its one condition, as 58 aimed at.
- `Overrides._counted_otherwise`, which compares what was given with what a column was counted
  with, then refuses every sentinel given that its column cannot hold; the message of
  `refuse_uncounted` names them, and says that the database writes the values of the type
  otherwise, such as `-1.0E0`, rather than that the column has no text.
- **What it costs.** A refusal where a scan today goes on. `sentinels: []` of a column of no text
  would no longer be refused, as an empty list is all held; it gives nothing it cannot be, so that
  this is no loss. The documents of the sentinels - `Column.sentinels`, `refuse_uncounted`, the
  recipe "Give the sentinels of a column" and the list of what is refused in PROJECT.md - change
  with it.

**Warn rather than refuse.** A warning names them and lets the scan go on. But an override that
cannot be what it gives is refused everywhere else, and a warning would be a second way beside it.

## Done when

A sentinel given of a column that its type cannot hold is refused by `scan`, naming the column and
the sentinels, whether the column has no text or a type that writes its values otherwise;
`statistics.count` decides by `Dialect.held` alone; and the documents say so.

## History

2026-11-12: Opened on the maintainer's request, from a design finding of the review of step 2 of
[58](58-the-configuration-of-a-project-its-class-and-its-examples.md), which recorded the silent
leaving aside as its outcome, but not as an option weighed.

2026-11-12: Done, as the issue preferred, chosen with the maintainer over a warning: `count`
decides by `Dialect.held` alone and records, of the sentinels given of a column, those its type can
hold, and `refuse_uncounted` refuses every other one given, naming each column, its type and the
sentinels, quoted - a column of no text is the case of holding none. The sentinels given are named
although they may be values of the database, as they are values of the overrides, which the
profile shows too. `sentinels: []` of a column of no text is no longer refused, as it gives nothing
it cannot be.
