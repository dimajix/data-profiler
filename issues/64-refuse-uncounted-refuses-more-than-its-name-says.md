# 64 — `refuse_uncounted` refuses more than its name says

**Status:** done
**Type:** refactoring
**Priority:** low
**Area:** Scan
**Summary:** `TableOverride.refuse_uncounted` is named after the sentinels a table was not counted with, but refuses as well a column the table does not have, a primary key of no columns or of one twice, and since issue 63 a separator of lists of a column of a type that holds no texts, so that its name does not say what a reader finds in it.

## The problem

`scan` calls `TableOverride.refuse_uncounted(table, dialect)` once it has counted a table, before it
takes its sample. Its doc comment says it "refuses what is given of `table` that it was not counted
with", and that held of the sentinels it was made for. What it refuses now:

- a column the overrides name that the table does not have, `_refuse_missing`;
- a primary key of no columns or of a column twice, `_refuse_primary_key`;
- sentinels given of a column that its type cannot hold, `_refuse_uncounted_sentinels`;
- a separator of lists given of a column of a type that holds no texts, `_refuse_unlisted`, added by
  [63](63-a-separator-of-lists-given-of-a-column.md), for which it takes the dialect.

Only the third is something the table "was not counted with". The others are what the overrides give
that cannot be of the table as it is counted - its columns and their types -, which is what all four
have in common.

## Why it matters

A reader looking for where a separator given of a column of numbers is refused, or a primary key of
a column twice, does not look in a method named after the sentinels; and the next refusal that has
to happen once a table is counted will be added to it as well, widening the distance between its
name and what it does.

## Considerations

- **Rename it** after what the four have in common: what is given that does not fit the table as
  counted. `refuse_unfit(table, dialect)` - "refuses what is given of `table` that cannot be of it,
  once it is counted" - is preferred: short, and it covers a refusal added later of the same kind.
  `refuse_after_counting` names when, not what, and says nothing a reader of `scan` does not see.
- **Split it** into a method per refusal, called by `scan` one after the other: more names for a
  reader of `scan`, who needs only that what is given is refused before the table is sampled, and
  one order to keep in the caller rather than in the owner. Not preferred.
- `_refuse_uncounted_sentinels` keeps its name, which is right of what it does.

**What it costs.** A rename of one method, its callers - `scan` and the tests of `overrides` -, the
module docs of `overrides` and its doc comment. No change of behaviour.

## Done when

The method `scan` calls once it has counted a table is named after what it refuses, its doc comment
and the module docs of `overrides` say so, and nothing else changes.

## History

2026-11-13: Opened on the maintainer's request, from a finding of the work on
[63](63-a-separator-of-lists-given-of-a-column.md), which added the fourth refusal.

2026-11-13: Done as preferred, as the maintainer agreed: `refuse_uncounted` is renamed
`refuse_unfit`, its summary line saying that it refuses what is given of the table that cannot be of
it, once it is counted; its callers, the module docs of `overrides` and the doc comment of
`statistics.count` name it so. No change of behaviour.
