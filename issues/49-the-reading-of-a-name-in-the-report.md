# 49 — The reading of a name in the report

**Status:** open
**Type:** feature
**Priority:** low
**Area:** Report
**Summary:** The report shows the harmonized name of a table or column but not its reading, the concept each term of the name stands for, so that a person cannot see how a name was understood, and not at all where no harmonized name comes of it.

## The problem

A name is split into terms, and its reading says which concept of the glossary each term stands for:
`cust_typ_cd` is read as `customer`, `type`, `code`. The profile holds the reading of every table
and column read, but the report shows only what is composed from it, the harmonized name.

The harmonized name does not show the reading:

- It does not say which term became which word, so a term of several concepts that was read wrongly
  has to be worked out by comparing the two names.
- The words of concepts marked as omitted are not in it.
- A name given by an override takes its place.
- Where a word of the reading is of no concept of the glossary, there is no harmonized name at all,
  and the report shows a dash though the reading exists.

## Why it matters

The report is where a person checks what the tool understood. A reading is what a person corrects in
the overrides, and the concepts behind it are what the glossary of the report explains, so that the
one link between the two is the thing missing. Today it can be found only in `profile.yml`.

## Considerations

**What is shown:**

- **Each term with its word**, `cust → customer · typ → type · cd → code`. It says what the
  harmonized name cannot, also where the words alone would repeat it. Recommended.
- **The words alone**, `customer type code`. Shorter, but for most names the same as the harmonized
  name beside it, and the term a word belongs to is left to the reader.
- **Omitted concepts are marked**, as the glossary of the report marks them, `(omitted)`: they are
  where the reading and the harmonized name differ. A term of digits stands for itself.
- **A reading that does not agree with its terms is not shown**, as `Glossary.harmonized` does not
  use it. A name without a reading shows nothing.

**Where it is shown:**

- **Under the harmonized name, in the cell of the name**, muted. It is read beside the name it
  explains and adds no column to a table of ten. Recommended. Tables show it the same way, beside
  the harmonized name of their heading, so that both are one rule.
- **A column of its own**, which is easy to scan, but makes the widest table of the report wider,
  for something most names need only a glance at.
- **A row of its own among the listed rows**, in a `details`, like the values. It stays out of the
  way, but it is hidden exactly where a person is comparing names, and it adds a row to every
  column.

## Done when

- The report shows, of every table and column read, each term of its name with its word, omitted
  concepts marked, also where the name has no harmonized name or has one given.
- A name without a reading, or with one that does not agree with its terms, shows none.
- Tests of the report show these cases.

## History

- **2026-11-10** — Opened, as the maintainer asked.
