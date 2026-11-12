# 61 — Enumerations given, and columns of types that are none

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Scan
**Summary:** Whether a column is an enumeration is decided by the count of its distinct values alone, so that a column of UUIDs, of dates, times or moments, or of floating numbers is taken for one where it has few values, and nothing can be given by hand to make a column an enumeration or none, where the tool decides otherwise.

## The problem

`enumerations.values` takes a column for an enumeration where the statistics counted at most
`_LIMIT` (500) distinct values in it, and not each of them in one row alone. Nothing else counts:

- **Its type.** A column of the database type `uuid`, `date`, `time`, `timestamp`, `real` or
  `double` of few values - the days of a monthly load, the UUIDs of a handful of tenants, a rate of
  a few steps - is an enumeration, its values in the profile, the report, the prompts of the
  language model and the data contract, which writes a rule that the column takes those values and
  no others. Values of these types are not drawn from a closed list: the next load brings a new
  day, a new UUID, a new number, and the rule of the contract breaks.
- **Its semantic type.** The same holds of a column of text whose values `detect` recognises as
  `uuid` or `date` - the UUIDs and dates written as text.
- **What a person knows.** An override can mark a column sensitive, give its sentinels, say that it
  determines none or refers to none, but not that it is an enumeration or that it is none. A column
  the tool takes wrongly for one cannot be taken out, and a column of codes the tool misses - each
  value in one row alone in a small table, or of a type the tool would leave out - cannot be put in.

## Why it matters

The values of an enumeration are what the profile shows of a column most plainly, and what the
contract turns into a rule. A wrong enumeration shows values that say nothing of what the column
is, and makes the contract refuse the next load of correct data; a missing one hides the codes of a
column, and keeps it from being a candidate of a discriminator. Where the tool decides wrongly,
the overrides are the one way to correct it for good, and here there is none.

## Considerations

**The override: `enumeration: true | false` of a column**, a field of `ColumnOverride`, taken by
`scan` like the sentinels: True makes the column an enumeration, False makes it none, whatever is
found; absent, the tool decides. The profile holds it as given, as it does the sentinels, so that
`agrees_with` tells a table counted otherwise and a scan resumed counts it again.

- **True of a column of more than `_LIMIT` values.** The limit keeps the database from grouping a
  column of keys of hundreds of millions of rows. Either True lifts the other conditions alone -
  each value in one row, the type - and the limit still holds, warned of where it is exceeded; or
  True lifts the limit too, and the person who gives it answers for the column; or the values are
  counted up to a limit, the most frequent first, which makes an enumeration of part of its values,
  a concept of its own. The first keeps the guarantee the limit gives, and is preferred.
- **False of a column given as the discriminator of its table.** A discriminator is an enumeration
  of no sensitivity; the two overrides contradict each other and are refused, as a discriminator of
  a column marked sensitive is.
- **A column of lists.** Its own values are never an enumeration, its texts being lists; the values
  of its lists are. Whether the override of such a column speaks of the values of its lists, or is
  refused there, is to be decided.

**The types that are no enumeration.** Of the database type, a question of the dialect, as all that
the tool knows of the types is: a predicate `Dialect.is_enumerable(kind)` - false of `uuid`, `date`,
`time`, `timestamp` and `real`, `double`, true of every other, `decimal` among them, whose values
are often codes of fixed digits. `values` asks no column of the types that are none. Of the semantic
type, a property of `SemanticType`, so that the rule sits with the type and not in a list of names
in `enumerations` - true of `uuid` and `date`, and to be decided for the types of the project, which
`project.yml` gives: a field of their definition, or no enumeration of them left out. A column of
lists judges the semantic type of the values of its lists.

**The order of the scan.** `values` counts the enumerations before the sample is taken and the
semantic types are recognised, so that it cannot ask them. Either the enumerations are counted after
`recognise` and `verify`, on the table with its semantic types, a reordering of `scan.scan` and of
`lists`, done as a step of its own before the feature; or they are counted as now and dropped
afterwards, by `valued`, which costs the queries of columns that are dropped and splits the decision
in two places. The first is preferred.

**What it costs.** One field of the overrides and its documents, one predicate of the dialect, one
property of the semantic types, and the reordering of the scan. Profiles scanned before lose the
values of the columns of the types left out only once `scan` counts their tables again.

## Done when

`overrides.yml` can give of a column `enumeration: true` or `enumeration: false`, taken by `scan`
as described, the profile holding it as given; a column of the database types `uuid`, `date`,
`time`, `timestamp`, `real` or `double`, or of the semantic types `uuid` or `date`, is no
enumeration unless the overrides make it one; and PROJECT.md, PROFILE.md and the doc comments say
so.

## History

2026-11-12: Opened on the maintainer's request: an enumeration given by override, true as well as
false, and no enumeration of UUIDs, dates, times, moments and floating numbers, by the database type
or the semantic type recognised.

2026-11-12: Decided with the maintainer: `enumeration: true` lifts the other conditions alone, the
limit still holds, and a column given so of more distinct values is warned of; the override of a
column of lists speaks of the values of its lists. The reordering of `lists` named above is not
needed: `lists` already counts the enumeration of the values of a list after their matches are
verified. And a column of lists does have an enumeration of its own texts, against what the
description says: `scan` counts the values of every column of few, its lists among them, before
it finds the columns of lists.

2026-11-12: The plan, agreed with the maintainer, in three steps. Step 0 counts the enumerations
of a table after its matches are verified, without a change of behaviour. Step 1 leaves out the
types that are none: `Dialect.is_enumerable` of the database type, false of `uuid`, `date`,
`time`, `timestamp`, `real` and `double`, and `SemanticType.enumerable`, false of `uuid` and
`date`, where any match of such a type leaves the column out, as any match of a sensitive type
makes it sensitive; `decimal` stays one, as its values are often codes, and the types of a project
too, as nobody needs a field of `project.yml` for it yet. A column of lists has no enumeration of
its texts any more, only that of the values of its lists. Step 2 gives the override,
`ColumnOverride.enumeration`, held by `Column.enumeration` as given, which
`TableOverride.laid_over` sets as it sets the marks, so that `agrees_with` tells a table counted
otherwise; it counts once `scan` counts the table again, and a discriminator of a column given as
no enumeration is refused.

2026-11-12: Step 0 done: `scan` counts the enumerations of a table after its matches are verified,
without a change of behaviour; a column of lists keeps the enumeration of its texts until step 1.

2026-11-12: Step 1 done: `enumerations.values` asks no column of a type that
`Dialect.is_enumerable` takes for none, of a match of a type that `SemanticType.enumerable` takes
for none, or of lists; the values of the lists of a column are enumerated as before.

2026-11-12: The test of step 1 through `scan` added, on the maintainer's request: the example
profile of the simulation has a column of few dates written as text, `cust_addr.chk_dt`, which
`scan` recognises as dates before it counts the enumerations, and so takes for none.

2026-11-12: Step 2 done, and with it the issue: `ColumnOverride.enumeration` gives whether a
column is an enumeration - of a column of lists, the values of its lists -, taken by
`enumerations.values` and `lists.itemize` through `TableOverride.enumerations`, and held by
`Column.enumeration` as `TableOverride.laid_over` gives it, so that a scan resumed counts a table
given otherwise again. True lifts the conditions of the type, the matches and the values each in
one row alone, not the limit: a column given so of more values is warned of, and none. A
discriminator given of a column given as no enumeration is refused. The formats of the profile and
of the overrides are raised to 14.6 and 7.7.
