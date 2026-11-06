# 43 — Columns of lists of values

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Scan
**Summary:** A column whose texts are lists of values, separated by semicolons - `12;47;3` -, is taken for a column of texts like any other, so that what its values are, whether they are values of a key of another table, and whether they tell kinds of rows apart is not found: each text is counted whole, as a value of its own.

## The problem

Some columns of the real database hold several values in one text, separated by semicolons:
`12;47;3`, `4`, `7;12`. So far the values seem to be numbers. The tool counts each text as a value
of its own: `12;47;3` and `47;12;3` are two distinct values, the column is no enumeration though it
holds few values, no detector recognises what the values are, as no pattern matches a whole list,
and no reference is found, as no text of the list is a value of a key. The language model is told
of a column of texts.

## Why it matters

A list of values in a column is a relation the data model does not show: most likely the values of
a key of another table - the products of an offer, the groups of a customer -, a relation of many
to many that a normalized model holds in a table of its own; or a set of codes - the roles of a
business partner, the channels a customer may be reached by -, each value of which may tell a kind
of rows apart, as a discriminator does, with the difference that a row may be of several. Both are
what epic [38](38-a-data-model-derived-from-the-profile-epic.md) is to derive a data model from, and
both are lost while the list is counted as a text.

## What is wanted

As the maintainer asked:

- **Recognised as a list.** A column whose texts are values separated by semicolons: no two
  semicolons in a row, and values of letters and digits alone, maybe with `-`, `+` and `_` - no
  spaces, no commas.
- **Each value matched.** The values of the lists are matched against the semantic types, as the
  texts of a column are, so that a list of numbers of currencies, of UUIDs, of codes is seen as
  such.
- **Each value a candidate of a discriminator, or the like.** The values of the lists are taken as
  the values of a column of their own - an enumeration, a candidate of a discriminator, a reference
  to a key -, not the lists.

## What is to be decided

- **What a column of lists is.** A semantic type, `list`, says what the texts are, but not what
  their values are, which is what is wanted. More likely it is a property of the column, as an
  enumeration is: its separator, and the values of its lists counted as a column of their own -
  their statistics, matches, enumeration, references -, held beside those of the texts. Its place
  in the profile, and the version of the format it raises, follow from that.
- **When a column is one.** A text of one value, `4`, is a list of one as well, so that a column
  of numbers would be a column of lists of none but one value. A share of the texts that hold a
  separator - at least one, a fifth, half -, or of the rows, is to be decided, and whether a
  separator at either end, `;12;47;`, as some systems write a list, is one too.
- **Which separators.** The semicolon alone, as the database holds it, or a few more - the comma,
  `|` - found the same way; a separator that a value can hold, the comma of a decimal, needs more.
- **The values in SQL.** On the whole table, the values of the lists are counted by splitting the
  texts in the database - `split` and `UNNEST` in Trino -, which the dialect writes: their distinct
  values, their matches, and their coverage of a key. Whether every query of a column that a scan
  sends has a counterpart of the values of a list, or only those named above.
- **A discriminator of lists.** A discriminator tells each row of one entity; a list of codes
  makes a row of several - a business partner both a customer and a supplier. Whether that is a
  discriminator, of entities a row may be of several of, or a concept of its own - roles of a row
  -, and what the data model derives from it, belongs to
  [36](36-entities-of-a-table.md) and epic [38](38-a-data-model-derived-from-the-profile-epic.md).
- **A reference of lists.** A list of values of a key of another table is a relation of many to
  many: whether `relate` finds the references of the values of lists as it finds those of columns,
  with their coverage, and whether the data model derives a table of the relation from it.
- **The order of the work.** Most likely in steps of their own: the column of lists recognised and
  its values counted and matched; then its references; then its discriminator, or roles. Whether
  this issue becomes an epic of them.

## Done when

- A column of lists of values separated by semicolons is recognised as one, as decided, and a
  column of texts or numbers without a list is not.
- The values of its lists are counted and matched against the semantic types, in a sample and on
  the whole table, and are candidates of a discriminator or a reference, as decided.
- The simulation environment holds columns of lists, and its test data generator writes them, so
  that each is recognised on the database.
- The profile, its document and the report show the column of lists and what was found of its
  values.

## History

- **2026-11-06** — Opened, as the maintainer asked: columns of lists of values separated by
  semicolons, so far of numbers, found in the real database; their values to be matched and to be
  candidates of a discriminator or the like.
