# 35 — References between tables

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Relate
**Epic:** [38](38-a-data-model-derived-from-the-profile-epic.md)
**Summary:** Nothing tells which columns of a table refer to the key of another - the customer of an order -, so that the relationships between the tables, which a data model is made of, are left to a person to find.

## The problem

The tables of the CRM declare no foreign keys, and Trino would name none. That `ord.cust_id` holds
the identifiers of `cust`, a person reads from the names, if the names are readable, and checks
nowhere. The epic of the first version left the relationships between tables out
([02](02-first-version-epic.md)).

## Why it matters

A reference is what makes a data model of separate tables: which entity belongs to which, and how
many of the one to one of the other. It is found in the data: a column refers to a key where its
values are among the values of the key - an inclusion dependency.

## What is to be decided

The interface first, put before the maintainer. It needs the keys of
[34](34-primary-keys.md).

- **Where it is found.** The references need the keys of all tables, not of the one counted: they
  are no work of `scan`, which counts table by table. Proposed: a stage of its own after `scan`,
  `relate`, which queries the database and writes the profile, as `scan` does; it would get an area
  of its own. Whether it uses the readings of the names `describe` leaves, if it ran - for the
  order of the candidates alone, so that it runs without `describe` -, and whether `describe` in
  turn shows the language model the references of a column.
- **The candidates.** Each pair of a column and a key of another table - or of the same, a parent
  of a hierarchy - of a type that compares; filtered by the profile, without a query: no more
  distinct values than the key, lengths and matches that agree, a range within the range of the
  key. The ranges are held of the columns of no sensitivity alone; whether those of the others are
  kept in the workspace for it.
- **A check without a query.** The distinct values of every key verified kept in the workspace, as
  Parquet, where sensitive values may be; the values of the sample of a candidate looked up in
  them, and only a candidate whose values are mostly found checked on the whole table. A pair of
  random samples of two tables says nothing: they hold few of the same rows.
- **Verified on the whole table.** By a query that counts the values of the column not found in the
  key, its nulls and sentinels left aside, built from the building blocks of the dialect: the
  coverage, as a share, not a yes or no, since real data hold rows whose reference is lost.
- **Codes that fit every key.** A status code of 1 to 5 lies within every key of integers from 1.
  Whether an enumeration is a candidate only where its name agrees - its reading names the concept
  the table of the key is read as -, or the coverage of the key is weighed: a column whose values
  fill a small part of the key is less likely a reference.
- **What the profile holds.** In the document of the table that refers, each reference with its
  columns, the table and key it refers to, its coverage, and its cardinality: whether one row or
  many refer to one of the key.
- **What the overrides give.** A reference the data do not show, and a reference found that is
  none, rejected, as a concept is omitted. A reference given is counted as one found is: its
  coverage and cardinality come from the data.
- **References to an entity.** In a table of several entities ([36](36-entities-of-a-table.md)),
  `ord.cust_id` may refer to the rows of one entity of `cust` alone; whether the coverage is counted
  per entity of the key.
- **The report** shows the references of each table, and what refers to it.

## How

As decided with the maintainer, in three steps - the profile and the simulation, the references
found, then those given:

- **The stage `relate`**, after `scan` and before `describe`, queries the database and writes the
  profile once at its end, without a run of its own: one that fails leaves the profile as it was,
  and the next begins anew. The module `references` finds them; the area is Relate. `scan` drops
  the references and candidates of a table it counts anew; those of others to it stay until
  `relate` runs again.
- **References of one column** alone, to a key of one column of a table, of another or the same.
- **The profile** holds, in the document of the table that refers, its `references`, one per
  column at most, and its `candidates`, of the columns of which several keys pass, in the order
  they are ranked, none of them preferred: each a `Reference` of the column, the table and key it
  refers to, its coverage and whether it was given. The cardinality is not held: a column that is
  a key of its table refers one to one, else many to one.
- **Unmistakable values**, of a type such as `uuid` or of a column whose match is a UUID, are
  equal to those of another column by no chance, so that one value found proves where they come
  from. Their coverage is of no interest, and not counted.
- **The candidates**, indicated without a query: of the keys of one column as targets, the columns
  of a type that identifies a row, of a family of types, distinct count, lengths, matches and range
  that agree with the key. A column of whole numbers whose values are a dense run at the start of
  the key, as a code or a counter is, stays a candidate only where its name agrees with the key.
  The ranges of sensitive columns are not needed: a sensitive column is no key.
- **The probe:** 100 values of each candidate, taken at random by `BERNOULLI` as the sample is -
  all candidates of a table in one read -, looked up in the whole key by Trino, so that no value
  leaves the database; batched, ten keys at most in a query, the result counts alone. A pair of
  random samples of two tables would say nothing. A candidate of unmistakable values refers to a
  key where more than half of its values probed are found; another is dropped below 80 %.
- **The coverage** of the other candidates is counted on the whole table: the values of the column,
  nulls and sentinels aside, found in the key, by joins built from the building blocks of the
  dialect, one read of the table for ten candidates at most. A candidate covered 90 % or more
  refers to the key.
- **Several keys:** of unmistakable values, the one of the most values found, then of the fewest
  rows, the most specific; of others, all kept as candidates, ranked by how the span of the values
  fits the one expected of a random choice of the key, by the original names - not the readings of
  `describe`, which runs after `relate` -, and by the fewest rows.
- **The overrides** give the reference of a column by the table and column it refers to, or
  `false` for none and no candidates. For a column given, nothing is searched; its coverage, or the
  probe of unmistakable values, is measured all the same, and warned of below the thresholds or
  where the column given is no key. A table or column the profile lacks is refused. No option
  searches what the overrides give.
- **The simulation** draws the values of a column of a reference from the key it refers to, a
  share of them outside of it as its coverage says, and its profile has keys of UUIDs, a reference
  of a table to itself, a code of whole numbers and keys of whole numbers sharing their values.

## Done when

- The interface is agreed with the maintainer.
- The references of the tables of the simulation are found, with their coverage and cardinality,
  and a code of a few values is not taken for a reference.
- The overrides give and reject references.
- The report shows them.

## History

- **2026-11-05** — Opened with [38](38-a-data-model-derived-from-the-profile-epic.md), as agreed
  with the maintainer.
- **2026-11-06** — The interface agreed with the maintainer (see How): a stage `relate` of its own,
  references of one column; the candidates indicated by the profile, probed by 100 values looked up
  in the whole key by Trino, and the coverage counted on the whole table of all but unmistakable
  values, such as UUIDs, which the probe decides; the targets of a column of several kept as
  candidates; the references given measured, not searched, without an option to search them.
- **2026-11-06** — Step 1 built: the profile holds the references and candidates of a table,
  `Reference` of the column, the table and key referred to, the coverage and whether it was given,
  its format raised to 13.3; it refuses a reference of a column or to a table or column it does not
  have, and a column of two references or of a reference and candidates, and drops those to the
  tables it no longer selects and to a column a table counted anew no longer has. The simulation
  draws each column from a random of its own, so that a column of a reference holds values of its
  key, as many rows outside of it as its coverage leaves; it keeps whole numbers within their range
  and makes UUIDs of the type `uuid`. Its profile numbers the keys of whole numbers from one, those
  of the products apart, and has keys of UUIDs, of the type and as text, a reference of the
  customers to themselves, codes of whole numbers, and the references of its tables.
- **2026-11-06** — After the review, the maintainer decided: `Table.candidates` keeps its name, as
  it means what `Term.candidates` means, possibilities of which one is to be chosen; what is
  indicated before it is verified is no candidate, in `keys` as in `references`, and `keys` is
  renamed so, in a commit of its own before step 2. The profile finds a table by its name,
  `Profile.table`, which the simulation takes its tables from; a column has a reference, candidates
  or neither, checked as the profile is read rather than a type of its own.
- **2026-11-06** — Step 2 built: the stage `relate`, `data-profiler relate ENVIRONMENT`, finds the
  references by the module `references` and writes them to the profile once, at the end; the dialect
  probes values taken at random in whole keys, `Dialect.probed` - the values taken held in memory,
  the keys read past them -, and counts the coverage, `Dialect.covered`, of `Probe` and `Lookup`,
  both comparing values as text, of types of one family, `Dialect.is_same_family`, and tells UUIDs
  by their type, `Dialect.is_unmistakable`. Unlike the How, each column probed is taken by a sampled
  read of its own, which ends once it has taken its values, rather than all of a table in one read.
  A range overlaps the key's, rather than lies within it, as the values outside of the key may lie
  beyond it. As the maintainer decided after the review, a run of whole numbers from the start of a
  key refers to it only where its name holds the terms of the key and of its table: a run short of
  the end of the key, as a code or a counter is, and one of a key of its own table, as keys numbered
  from one are within each other; a column of nearly every value of the key refers to it whatever
  its name. `Profile.read_of` reads a profile of a schema, for `scan` and `relate`. The report shows
  the references of a table, one to one or many to one, as `Table.cardinality` says, its candidates
  ranked, and the references to it, as `Profile.referring` gives them. In the simulation, the
  references of UUIDs, of the products, of the addresses to their customers and of the items to
  their orders are found; the customers of contacts and orders are candidates of every key numbered
  from one, the customers first, and no code refers to a key.
- **2026-11-06** — Step 3 built: the overrides give the reference of a column, `reference: {table:
  cust, column: cust_id}`, or `reference: false` for none, `ColumnOverride.reference`, their format
  raised to 7.3. `relate` takes them by `Overrides.references`, which refuses a table or a column
  the profile does not have, a reference to one and one of a column to itself, before anything is
  queried, as the stages that read the profile refuse them: a column given is not searched, but
  measured, its coverage counted or its values probed, and warned of where that falls below what a
  reference is found at or where the column referred to is no key of one column, and the profile
  holds it as given; a column given none has no reference and no candidates. A stage that reads the
  profile warns of a reference given otherwise than the profile was related with, and the report
  marks the references given. The example gives the contact person of a customer and the customer of
  an order, which keys numbered from one hold as candidates, and none of the number a business
  partner has as a customer elsewhere.
