# 56 — A column of one value in the report

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Report
**Summary:** A column that holds the same value in every row of its table looks in the report like any other column, so that a person reading a table has to work out from its distinct count and its shares of nulls and sentinels which of its columns tell no row from another.

## The problem

Since [54](54-a-column-of-no-information-in-the-report.md), a column filled in no row of its table
is marked in the report as of no information: a light grey background, dark grey text, and the
words `no information` in the column *Range*. A column filled in every row with one and the same
value says hardly more: which value it is, once - but nothing about any one row that it does not say
about every other. The report shows it only in its numbers: a distinct count of 1, and shares of
nulls and sentinels of 0%.

The maintainer asked for such a column to be marked as well, as the columns of no information are,
on a slightly different grey, so that the two can be told apart.

## Why it matters

As with the columns of no information: wide tables of legacy databases carry columns that were
filled with a default and never with anything else - a flag always `N`, a client always `100`, a
currency always `EUR`. Marked, they can be passed over at a glance; and a column that is constant by
mistake, where values were expected to differ, stands out.

## Considerations

**What counts as a column of one value.** One value in every row of its table: filled in every
row - `table.filled(column) == table.rows`, the method of
[55](55-the-rows-a-column-is-filled-in.md) - and of one distinct value, `statistics.distinct == 1`.

- **Never empty, as asked.** A column of one value and nulls, or one value and sentinels, is not a
  column of one value: which rows hold the value and which none is information. Sentinels count as
  nulls here, as they do for *filled*, and the distinct count of the statistics leaves them aside.
- **The distinct count is approximate**, as `approx_distinct` counts it. For a handful of values the
  estimate of the database is exact in practice, so that 1 is one value. Where the profile holds
  the enumeration of the column, it is counted exactly and could confirm it - one value, in every
  row -; but an enumeration is in the profile only as `disclosure` lets it, so it cannot be the
  rule. Recommended: the distinct count alone; the enumeration, where shown, agrees with it.
- **A table of one row.** Every column filled in it is of one value. Marking them all says nothing
  the `1 rows` of the table does not; recommended, as for a table of no rows in 54: a table of one
  row marks none of its columns.
- **A column of lists** of the same list in every row is a column of one value as well; the
  statistics count its lists, not the values in them. Nothing to tell apart.

**Where the rule lives.** In the template, beside `no_information`, as decided in 54: the template
is its only user. Both rules are about the rows filled, and both ask the table for them.

**The look.** A background of its own, `--one-value` beside `--no-information`, the text in
`--muted` as there. The grey has to be told apart from `--no-information`, from `--head` - the grey
of the header row - and from white, on screen; three greys close to each other are hard to tell
apart.

- **A lighter grey than that of no information**, so that the column that holds nothing is the
  darker one, the column that holds one value the lighter. Recommended.
- **A grey of another hue**, a warm grey beside the neutral one, which tells them apart more surely
  than lightness alone, at the cost of a colour that means nothing of its own.

**Said in words, not only in colour,** as in 54, since the background is not printed: the words
`one value` in the column *Range*, where the sensitivity of a sensitive column and the
`no information` of an empty one stand. The value itself is in the list of the values below the
column, where the profile holds its enumeration. Alternatively `one value: B`, from the range of
the column; but a range is not known of a column whose values have no order, and an end of it may
be withheld, so that the words would differ by what the profile holds. Recommended: `one value`.

**A column sensitive and of one value** is shown as sensitive, as in 54: its sensitivity in the
column *Range*, and not as of one value. A column cannot be of no information and of one value at
once - filled in no row and in every row of a table of rows.

## Done when

- A column filled in every row of a table of more than one row, with one distinct value, is shown
  on a grey background of its own, told apart from that of a column of no information, its text in
  dark grey, in every row that belongs to it, and says `one value` in the column *Range*.
- A column of one value and nulls or sentinels, a column of a table of one row, and a sensitive
  column are not shown as of one value.
- Tests of the report show the cases above.

## History

- **2026-11-11** — Opened, as the maintainer asked.
