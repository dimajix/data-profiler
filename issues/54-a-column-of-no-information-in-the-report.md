# 54 — A column of no information in the report

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Report
**Summary:** A column that holds nothing but nulls and sentinels looks in the report like any other column, so that a person reading a table has to work out from its shares of nulls and sentinels which of its columns say nothing at all.

## The problem

A table of the report lists every column alike. A column whose rows are all null, or null and a
sentinel - `''`, `'9999-12-31'` -, holds no information: whatever its name and type promise, no row
of the table has a value in it. The report shows this only in its numbers: the shares of nulls and
sentinels, which add up to 100%. A reader sees it only by adding them up, column by column.

The maintainer asked for such a column to be marked as the sensitive ones are: its row on a light
grey background, as a sensitive one is on a red one, and its text in a dark grey instead of black -
so that it reads as *holds no information*, and steps back behind the columns that do.

## Why it matters

The report is read to find out what a table holds. Wide tables of legacy databases carry many
columns that were once planned and never filled; among the columns that hold something, they take
the eye as much as those. Marked, they can be passed over at a glance - and the columns that are
empty by mistake, where values were expected, stand out.

## Considerations

**What counts as no information.** A column is *filled* in a row where it holds a value, neither
null nor a sentinel - the word the profile already uses (`Entity.filled`, `ColumnGroup`). A column
of no information is one filled in no row of its table: `nulls + sentinel_rows == rows`, by the
statistics, which are counted on the whole table. The sentinels are those the column was counted
with, the tool's or those given by the overrides; a column whose values the database writes as no
text has none, so only its nulls count.

- **A table of no rows.** Every column of it is filled in no row. Marking them all says nothing the
  `0 rows` of the table does not; decided: a table of no rows marks none of its columns.
- **A column of one value only**, filled in every row with the same value, holds little information
  too, but it holds some - which value it is. It is not part of this issue.

**Where the rule lives.**

- **In the template**, as the expression above, named by a variable of the loop over the columns.
  Decided: the template is its only user, once the report says it of each column in words rather
  than by a count in its summary (below), which `render` would have to compute by the same rule.
  Should a second user come - `describe`, which might not ask the language model for a description
  of a column that holds nothing -, it moves to `Table`, which knows both the rows and the
  statistics of its columns.
- **A function of `report`**, given to the template as `limit` is (`_limit`). Needed only if the
  summary counts the columns of no information, so that the count and the mark share the rule; a
  helper with a single caller otherwise.
- **A method of `Table`** from the start. It is where the rule belongs by subject, but has no second
  user yet.

**What is marked.** The sensitive class marks the row of the column alone; the rows of its values,
its lists and its sentinels below it stay white. A column of no information has, at most, the row
of its sentinels below it. The maintainer asked for "these parts of the table" to be grey, which
reads as all rows of the column.

- **All rows of the column**, for a column of no information and, in the same change, for a
  sensitive one, so that both marks work the same way. One `<tbody>` for each column, the
  alternative weighed in [48](48-the-values-of-a-column-in-the-report.md), would give the class one
  place instead of one per row. Decided.
- **The row of the column alone**, as the sensitive class does today. Smaller, but the row of the
  sentinels then reads as not belonging to the grey column.

**The look.** A background of its own, `--no-information` beside `--sensitive`, a light grey told
apart from `--head`, the grey of the header row; the text in `--muted`, the dark grey the report
already uses for what steps back.

**Said in words, not only in colour.** A browser prints no backgrounds unless told to, and a colour
alone says nothing to a reader who does not know what it means. The sensitive columns are told by a
word as well - their sensitivity in the column *Range*, and their count in the summary of the
report.

- **A count in the summary**, `· 4 columns of no information`, and `title="holds no information"`
  on the row. The count puts the rule in `render` as well; the title is not printed.
- **The words `no information` in the column *Range*,** where the sensitivity of a sensitive column
  stands. A column of no information has no range - the profile keeps none of a column of nulls and
  sentinels alone -, so the cell shows a dash otherwise. Printed, at the row it is about, and in the
  template alone. Decided.

**A column sensitive and of no information.** It can only be marked sensitive by the overrides, as
no match is found in a column of no values. The mark is a deliberate statement: decided, it is shown
as any sensitive column is, its sensitivity in the column *Range*, and not as of no information.

## Done when

- A column filled in no row of its table - every row null or a sentinel - is shown on a light grey
  background, its text in a dark grey, in every row that belongs to it.
- A column of a table of no rows, and a column filled in at least one row, are shown as before.
- Such a column says `no information` in the column *Range*.
- A sensitive column of no information keeps its red background.
- Tests of the report show the cases above.

## History

- **2026-11-11** — Opened, as the maintainer asked.
- **2026-11-11** — The maintainer decided for the rule in the template and the words
  `no information` in the column *Range*, without a count in the summary.
- **2026-11-11** — Done: a variable of the template marks a column filled in no row of a table of
  rows; each column is a `<tbody>` of its own, which carries the mark, `sensitive` or
  `no-information`, over all of its rows.
- **2026-11-11** — The review found the arithmetic of the rule computed in `references` as well, as
  the rows a column has present; moving it to `Table` is
  [55](55-the-rows-a-column-is-filled-in.md).
