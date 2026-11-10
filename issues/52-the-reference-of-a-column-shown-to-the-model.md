# 52 — The reference of a column shown to the model

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Describe
**Summary:** The question for the description of a column does not show the language model the reference of the column to a key of another table, though the profile holds it.

## The problem

The stage `relate` finds which key a column refers to, and it runs before `describe`, but the
question for the description of a column, `description.txt`, shows nothing of it. Whether `describe`
shows the model the references of a column was left open by
[35](35-references-between-tables.md).

## Why it matters

Names of columns such as `prtnr_no` or `cust_ref` say little by themselves. That the column refers
to a key of a table of customers says what it stands for, and is a fact found on the data of both
tables, not a guess from the name.

## Considerations

What is shown of the key referred to:

- **The names of its column and its table alone.** Needs the template alone, but a name of
  abbreviations such as `cust` says little to the model.
- **With the reading of the name of its table.** Says what the table is. It needs the table referred
  to in the template, and its reading is there for every table, as the names are read before any
  column is described. Decided.
- **With the description of its column.** A column is described only once those before it are, so
  that what the model is shown would hang on the order of the tables, and a column referred to from
  an earlier table would not have one yet. Rejected.

Reference candidates are not shown: of several keys, none is the one, and the model would write one
of them into the description as if it were a fact.

## Done when

- The question for the description of a column of a reference shows its key and its table, and the
  name of that table in words where it is read.
- A column of no reference, or of reference candidates alone, is asked about as before.
- `docs/ARCHITECTURE.md` says so where it describes what the model is shown.

## History

- **2026-11-10** — Opened at the request of the maintainer, who decided what is shown: the key, its
  table and the reading of the name of that table, and no reference candidates.
- **2026-11-10** — Done, as decided. `description.txt` shows the reference as one line among the
  facts of the column, `- refers to: the column "cust_id" of the table "cust", whose name reads:
  customer`, the name of the table as `Glossary.harmonized` gives it, a name given among them. The
  template is given the profile with the overrides laid over it, to reach the table referred to.
  The closing instruction of the question is unchanged, and the wording was not tried on a model.
