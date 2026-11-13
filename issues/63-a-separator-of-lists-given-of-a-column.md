# 63 — A separator of lists given of a column

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Scan
**Summary:** The separator of lists is given of the project and of a table alone, so that the columns of a table whose lists are of different separators cannot all be found, and a column the tool takes wrongly for one of lists, or misses, cannot be corrected by an override of the column, nor a table of no lists be given none where the project gives one.

## The problem

Since [43](43-columns-of-lists-of-values.md), `project.yml` gives `list_separator`, the same in all
tables, and an override of a table one in its place. `scan` finds the columns of lists of a table by
that one separator, `lists.listed`; `ColumnOverride` has no field of it. So:

- **A table of lists of two separators.** A table whose column `product_ids` holds `12;47;3` and
  whose column `channels` holds `mail|phone` has one of the two found, never both.
- **A column taken wrongly for one of lists.** A column of codes that happen to hold the separator -
  `A;B` as a code of its own - is taken for one of lists, its texts no enumeration, its values
  counted as items. Nothing given of the column takes it out; the one way is to give its table
  another separator, which loses the other columns of lists of the table.
- **A column missed.** A column whose sample holds lists, but too few of them to be one, as
  `detect.is_list` judges, cannot be made one.
- **A table of no lists.** A table override cannot say that the table has none, where the project
  gives a separator: `scan.scan` takes `given[name].list_separator or list_separator`, so that None,
  not given, falls back to that of the project.

## Why it matters

The columns of lists are what the values of a relation of many to many, and the values of a
discriminator of several kinds per row, are found in. Where the tool decides wrongly of a column,
the overrides are the one way to correct it for good, as they are of its sensitivity, its sentinels,
its enumeration and its reference; of its lists there is none. No such table is known in the real
database yet; the question was raised by the maintainer.

## Considerations

**The override: `list_separator` of a column**, a field of `ColumnOverride`, of the same name as of
the project, the table and the column of the profile, one name of the concept everywhere. Of the
form `ListSeparator or false`, as `reference` and `discriminator` are: a separator makes the column
one of lists of it, `false` makes it none, whatever is found; absent, the separator of the table,
else of the project, decides, as now. The column comes before the table, the table before the
project.

- **A separator given: found by it, or taken as given.** Either the column is a list of it whatever
  its sample holds, as a primary key given is taken whether its values are unique, warned of where
  its texts are no lists of it - consistent with the other overrides, which hold "whatever is
  found" -; or the separator given replaces that of the table for the column alone, and the column
  is still found by it or not, which corrects the first case above but not the third. The first is
  preferred: it answers all three cases, and `enumeration: true` is taken the same way.
- **A table given no separator.** The same form for the table, `list_separator: false`, makes it of
  no lists whatever the project gives. It is a field the overrides of the table already have, given
  one more value, and answers the fourth case; a separator of every column `false` would answer it
  too, but column by column.
- **Telling a table counted otherwise.** `lists.is_listed_with` judges a table by one separator;
  with separators of columns it judges each column by its own, the one given, else that of the
  table, else that of the project, so that the logic moves into the override of the table, which
  then knows the separator of the project to judge by, or is handed it. Where the decision of a
  column of no lists cannot be told - a column given `false` that holds none anyway - the table is
  counted anew in the next run, as a separator changed is now.
- **The profile holds it as given**, at the column, `list_separator`, as it does now; whether it
  was given or found need not be held, as long as `scan` can tell from the overrides whether the
  table agrees.

**What it costs.** One more value of a field of the overrides of a table, one field of those of a
column, the separator of each column decided by `lists.listed` rather than one of the table, the
judgement of a table counted otherwise extended to the columns, and PROJECT.md and the doc comments.
No change of the format of the profile.

## Done when

`overrides.yml` can give of a column `list_separator` as a separator or `false`, and of a table
`list_separator: false`, taken by `scan` as decided, the column before the table before the
project; a scan resumed counts anew a table whose columns are given another separator than they
were counted with; and PROJECT.md and the doc comments say so.

## History

2026-11-13: Opened on the maintainer's request: a separator of lists given of a column, as so far
only the project and a table give one.
