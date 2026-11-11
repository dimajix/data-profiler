# 55 — The rows a column is filled in

**Status:** done
**Type:** refactoring
**Priority:** low
**Area:** Profile
**Summary:** How many rows of its table a column is filled in - holds a value, neither null nor a sentinel - is computed from its statistics in two places, `references` and the template of the report, under two names, "present" and "filled", instead of being asked of the table.

## The problem

A column is *filled* in a row where it holds a value, neither null nor a sentinel: the word the
profile uses for it (`ColumnGroup`, `Entity.filled`). How many rows of its table a column is filled
in follows from the rows of the table and the statistics of the column:
`rows - nulls - sentinel_rows`. Neither `Table` nor `Column` offers it, so it is computed where it
is needed:

- **`references`**, by `_present(table, column)` (`references.py`), which `_Pair.present` and the
  choice of the pairs to probe (`present > 0`) use: a column filled in no row refers to nothing.
- **The template of the report**, since [54](54-a-column-of-no-information-in-the-report.md), as
  `statistics.nulls + statistics.sentinel_rows == table.rows`: a column filled in no row is marked
  as of no information.

The same arithmetic in two modules, and the concept under two names: "present" in `references`,
"filled" in the profile, its documents and the report.

## Why it matters

The rule of what counts as filled is one rule. Should it change - a sentinel counted differently,
the rows of the lists of a column of lists -, it has to be found and changed in both places, and
the reader of either has to know that the other exists. The principles *No repeated logic* and
*Concepts are named* (AGENTS.md) ask for one place and one name.

## Considerations

- **A method of `Table`**, `filled(column: Column) -> int` - how many of its rows `column` is
  filled in, neither null nor a sentinel. `Table` knows both its rows and the statistics of its
  columns. `references` uses it in place of `_present`, which goes, and `_Pair.present` is renamed
  `filled` with it; the template asks `table.rows and table.filled(column) == 0`. Recommended. It
  adds to the public interface of `Table`, which is why it was not done in 54 on its own.
- **Taking the name of the column**, `filled(name: str)`, as `Table.column(name)` does. `_Pair`
  holds the column of a table of the profile, but `_present` is called with `self.table.column(...)`
  as well as with a column at hand; which fits both callers better is to be seen in the plan.
- **A property of `Column`.** A column does not know the rows of its table, so it cannot.
- **Nothing.** Two places of one line each; but the second came without the first being seen, which
  is exactly what one place prevents.

A refactoring without a change of behaviour: the report and the references found stay as they are.

## Done when

- How many rows a column is filled in is computed in one place, offered by the profile, and called
  "filled" everywhere.
- `references` and the template of the report ask it there; `_present` is gone.
- The tests pass unchanged, and a test of the profile shows the method.

## History

- **2026-11-11** — Opened, as the maintainer asked, from a finding of the review of
  [54](54-a-column-of-no-information-in-the-report.md).
- **2026-11-11** — Done, as the first consideration recommends, by the name of the column, as
  `Table.column` and `Table.reference` take one: `_Pair` holds its column as the column of the
  values of its lists, whose statistics are not those of its rows, so that a method taking a column
  could be handed the wrong one unnoticed. `Table.filled(name)` replaces `_present`, `_Pair.present`
  is `_Pair.filled`, and the template of the report asks the table. The rows filled that
  `matching` counts anew, by the query that verifies the matches, are called so as well.
