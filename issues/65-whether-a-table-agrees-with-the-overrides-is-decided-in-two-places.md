# 65 — Whether a table agrees with the overrides is decided in two places

**Status:** open
**Type:** refactoring
**Priority:** low
**Area:** Scan
**Summary:** Whether a table a resumed run counted agrees with the overrides is decided by `TableOverride.agrees_with` and, for the separator of lists, by `lists.is_listed_with`, joined in `scan`, as the overrides of a table do not know the separator of the project, so that one question has two owners and a caller that has to know both.

## The problem

A run resumed skips a table it counted where the table agrees with what is now given:

```python
separator = given[name].separator(list_separator)
kept = profile.counted(name)
if kept is not None and given[name].agrees_with(kept) and is_listed_with(kept, separator):
```

`TableOverride.agrees_with` judges the marks, sentinels, enumerations, separators of lists given of
the columns, primary key, columns determining none and discriminator; `lists.is_listed_with` judges
whether the columns given no separator were counted with the separator of the table, else that of
the project. The second is apart only because a `TableOverride` does not know the separator of the
project, which `project.yml` gives and `cli` hands to `scan`; its doc comment says so. Since
[63](63-a-separator-of-lists-given-of-a-column.md) the two halves meet within one column: whether a
column is judged by `is_listed_with` depends on whether `agrees_with` judges it, by
`Column.list_separator_given`.

## Why it matters

A question of one sentence - does this table agree with what is given? - has two owners, and its
caller has to know that both are needed and how they divide the columns. A new override taken by
`scan` must be judged in one of the two, and whoever adds it has to find which. And `lists`, a
module of finding the columns of lists, holds a rule of the overrides.

## Considerations

- **`agrees_with` takes the separator of the project**, `agrees_with(table, project)`: it decides
  the separator of the table by `separator(project)`, which it already owns, and judges the columns
  given none by it, as `is_listed_with` does now. `is_listed_with` moves into `overrides` as a
  private function, since `lists` imports `overrides` since issue 63 for `GivenSeparators`, and
  `overrides` cannot import `lists` back. `scan` asks one question. Preferred.
- **The overrides hold the separator of the project**, given to `Overrides` when `cli` makes them:
  `agrees_with` keeps its signature, but `Overrides` holds a setting of another document, and every
  test that makes overrides has to give it. Not preferred.
- **Leave it**: the division is documented in both doc comments. It costs nothing now, and the cost
  grows with each override `scan` takes.

**What it costs.** One parameter of `agrees_with`, `is_listed_with` moved and its tests with it, the
callers of `agrees_with` - `scan` and the tests -, and the doc comments and the module docs of
`overrides`, `lists` and `scan`. No change of behaviour.

## Done when

`scan` decides whether a table counted by the run resumed is skipped by one method of the overrides
of the table, which judges the separator of lists of its columns as well; `lists` holds no rule of
the overrides; and the doc comments say so.

## History

2026-11-13: Opened on the maintainer's request, from a finding of the work on
[63](63-a-separator-of-lists-given-of-a-column.md).
