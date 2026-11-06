# 43 — Columns of lists of values

**Status:** in progress
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

## What is decided

As the maintainer decided on the questions below, and on the plan of the work:

- **A column of lists is a property of the column**, not a semantic type: its separator, and in
  step 2 the values of its lists counted as a column of their own. It is no part of epic
  [38](38-a-data-model-derived-from-the-profile-epic.md), as it is needed before.
- **When a column is one**: nearly every text of the sample, 95 percent as of the codes of
  currencies, is a list, of one value or more - a text of one value is no evidence against a list -,
  and one text at least holds the separator. A separator at either end is none, as the database
  holds none.
- **The separator is configured, not guessed**: `list_separator` in `project.yml`, the same in all
  tables of a system, and in the overrides of a table in its place; one character, no letter,
  digit, `-`, `+` or `_`. A project without one has no columns of lists. The profile holds it at
  the column, `list_separator` as well, one name of the concept everywhere, so that `relate` reads
  it from the profile.
- **A discriminator of lists**: the values of the lists are candidates as the values of a column
  are; several values belong to one entity anyway, so that no contradiction is seen for now. The
  texts of a column of lists are no candidate - which is how the problem was seen: a column of
  lists was taken for a discriminator.
- **References of lists**: `relate` finds the references of the values of lists to a key, a
  relation of many to many.
- **Three steps**, one issue: first the separator and the columns of lists found - as the
  separator alone would be a setting nobody reads -, with the profile, the report and the prompts
  showing them, and no column of lists a candidate of a discriminator; then the values of the lists
  counted, matched, and candidates of a discriminator, in the sample and by `UNNEST` on the whole
  table; then their references.
- **A changed separator** counts the tables anew in the next run; a run resumed counts anew those
  whose columns of lists are of another separator than now given, as a table of no lists cannot
  tell which it was counted with.

- **Step 2**, as the maintainer decided on its plan: a source in which a table is read as one row
  of each value of the lists of one of its columns, `Source.unnested`, so that `statistics`,
  `enumerations`, `matching` and `entities` count the values of the lists as they count a column,
  rather than queries of their own, which would repeat them; the values in the profile as `Items`
  of a column, `Column.items` - their statistics, matches and values -, not a column of its own,
  whose name, terms and descriptions they lack; a list of a sensitive type sensitive as its column
  is; keys and column dependencies of the texts alone. In three parts: 2a, every statement of the
  dialect reading a table by one method, without a change of behaviour; 2b, the values of the
  lists counted, matched and shown; 2c, a discriminator of the values of a list.

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

- **2026-11-06** — Step 1 done: `list_separator` in `project.yml`, in a `TableOverride` and at a
  `Column` of the profile, of one type, `profile.ListSeparator`, which refuses what cannot be one
  as `detect.is_list_separator` says; `detect.is_list` takes the texts of a column for lists as a
  detector does, of the threshold of the codes of currencies; the new module `lists` finds the
  columns of lists of a table in its sample, and `scan` counts anew a table of a run resumed whose
  lists are of another separator; `entities` takes no column of lists for a candidate; the report
  and the prompts show the separator; the example profile has `cust.grp_ids`, the example project
  `list_separator: ";"`. The versions: the profile 14.3, `project.yml` 4.1, the overrides 7.5. The
  generator of the references of the documents writes a type checked once it is read as the type
  it is read as. Found in the review: only a column of text is one of lists, as a decimal written as
  text, `12.50`, would be a list of a dot.

- **2026-11-06** — Step 2a done: the dialect of Trino reads every table after a `FROM` by
  `_relation`, the table itself so far; the statements are what they were.

- **2026-11-06** — Step 2b done: `Source.unnested` reads a table as a row of each value of the
  lists of a column, its dialect writing the table as a statement of `UNNEST` of its own; the
  module `lists` counts the values, `itemize`, by `statistics.count` - which counts the columns
  asked for alone, so that the values are not counted with every column of the table -,
  `enumerations.values` and `matching.verify` on that source, recognised in the texts of the sample
  split at the separator; `valued`, moved from `scan` to `enumerations`, gives the values of their
  enumeration. The profile holds them as `Items` of a column, of version 14.4; a match of them of a
  sensitive type makes the column sensitive, and `disclosure` withholds their range and values as
  the column's. The report and the prompts show their number and types. The example profile has
  the items of `cust.grp_ids`, and `prod.sale_curr_cds`, lists of codes of currencies; the
  generator draws the values of the items first, then the lists of them, each value of the items
  in one at least. Found in the review: a text of a column of lists is withheld where one of the
  values of its list is of a sensitive type, as an IBAN in a list would have gone into the profile;
  a profile scanned with other semantic types drops the matches and values of the items as well;
  the items are counted with the sentinels given of their column; `enumerations` and `matching`
  log the name of the source of a table, so that those of the values of a list are told apart.

- **2026-11-06** — A restructuring before step 2c, as the maintainer decided after the review of
  2b, without a change of behaviour: statistics, matches and values were a triple of a column and of
  its items alike, whose rules were written twice - the sensitivity, what a sensitive column keeps,
  what other semantic types drop - and the second copy had been missed once. `Items` became
  `Findings`, what was found of values, with `sensitivity` and `unmatched`; a column shows what was
  found of its own values as `Column.findings`, and `Column.applied` makes one change to them and
  to its items alike, so that `disclosure` - which keeps the rule of what a sensitive column keeps,
  `_withheld` - and `Profile.updating` cannot change the one and miss the other. The document of
  the profile is as it was; a field of findings in place of the flat fields of a column would
  change its format, a major version, and is not done.

- **2026-11-06** — Step 2c done: of a column of lists, the values of its lists are a candidate of a
  discriminator, by `Column.as_items`, the column as one of the values of its lists; `entities`
  counts each such candidate on a source of a row of each value of its lists, the other candidates
  in one query as before, so that a row is counted with each value of its list: the rows of an
  entity may be more than its own, and those of its entities more than those of the table, as
  `Entity.rows` says; the report takes the rows of no entity from `Table.rows_of_no_entity`, which
  tells none of them. A discriminator given of a column of lists is of the values of its lists
  alike; `disclosure` keeps it where the column keeps them. The report says that the entities are of
  the values of the lists, and tells no rows of none of them. The simulation generates no
  discriminator of lists, and refuses one, so that it is tested by tables made by hand and the query
  on the database by the scan of the example profile, whose columns of lists are candidates, of
  entities of none.
