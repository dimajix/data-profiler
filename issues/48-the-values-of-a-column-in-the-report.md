# 48 — The values of a column in the report

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Report
**Summary:** The line that separates the columns in a table of the report runs between a column and its values instead of below them, and a column of nothing but UUIDs lists all of its values, up to 500, where five say all there is to see.

## The problem

**The line.** A column of a table in the report is a row, followed by up to three rows of what was
listed of it: its values, the values of its lists, its sentinels. Every cell has a line below it,
but the rows of `.values` have none (`report.css`). So the line runs directly below the row of the
column, between it and its values, and none follows the last of them: the values read as if they
belonged to the column below, whose row they touch. The line is to run below the values, or below
the row of the column where nothing is listed of it, and nowhere between a column and its values.

**The UUIDs.** A column is an enumeration if it has at most 500 distinct values and not each of them
in one row alone, and the report lists every value of an enumeration. Of a column that holds nothing
but UUIDs, that is a list of up to 500 values of which any one looks like the next. Five are enough
to show what is in it.

## Why it matters

The report is read to find out what a column holds. A line in the wrong place attaches every list
of values to the wrong column, on every table with an enumeration. A long list of UUIDs says nothing
that its first five do not, and takes the room of what does.

## Considerations

**The line:**

- **One rule of the styles**, `tr:has(+ .values) td { border-bottom: none; }`, in place of the rule
  that takes the line off the rows of `.values`: a row followed by a row of values has no line, so
  that the last row of a column has it, whichever that is. Nothing of the template changes.
  Recommended. `:has` is in every browser since the end of 2023.
- **One `<tbody>` for each column**, the line on the last row of each. It says in the markup that
  the rows belong together and needs no `:has`, but changes the template for what is one rule of
  the styles.

**The five values:**

- **Cut in the report, not in the profile.** The profile keeps the whole enumeration: the values of
  a discriminator are checked against it (`disclosure.py`), and the report renders what the profile
  holds. Cutting at the scan would make the profile depend on how it is shown. Recommended.
- **What counts as nothing but UUIDs:** a match of the semantic type `uuid` with a share of 100% of
  the sample, and of 100% of the table where the table was verified. A column of the database type
  `uuid` has no share of the table, as only columns with text are verified, and counts by its
  sample. A column of 95% UUIDs lists all its values, as what does not fit is what is worth seeing.
- **The values of the lists of a column** follow the same rule by their own matches. Sentinels do
  not: they are no values of the column, and each of them says something.
- **Which five:** the first, the most frequent, in the order of the profile.
- **The line of the list has to say so:** `5 of 312 values`, not `5 values`, or the report states
  something false about the column. Where a column has five or fewer, nothing changes.

## Done when

- In a table of the report, no line runs between a column and its values, and a line runs below the
  last row of every column, with values and without, on screen and in print.
- A column of nothing but UUIDs lists its five most frequent values and says how many there are; so
  do the values of the lists of a column.
- A column that is partly UUIDs, and all sentinels, are listed in full.
- The profile is unchanged, and tests of the report show the cases above.

## History

- **2026-11-10** — Opened, as the maintainer asked.
