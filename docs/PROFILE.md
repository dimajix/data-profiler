# The profile

What the tool found about the tables of one schema of a database: the profile, which the stages
hand to each other, and which a person reads, shares and keeps in version control. This document
says how a profile is laid out, which stage fills what, what it never holds, and ends with the
reference of every field, generated from the classes the tool reads and writes it by. What a
developer writes of a project - its configuration and its overrides - is described in
[PROJECT.md](PROJECT.md).

## The directory of a profile

A profile is a directory of YAML documents, `profile/` in the directory of an environment:

*   **`profile.yml`** holds the profile but its tables: the catalog and the schema, the last run of
    `scan`, the glossary, and the semantic types of the project.
*   **`tables/<table>.yml`** holds a table, in a file named after it, so that a person finds a table
    in a file of its own and its changes in a diff of their own. A table whose name is no name of a
    file on every system is refused. A file of a table is read with the semantic types of
    `profile.yml`, which its matches name.

A field that has its default is not written, so that a document holds what differs from the
defaults. A profile is written by the tool alone; a correction goes into the overrides of the
project, which every stage lays over the profile it reads.

## What the profile never holds

**No values of the columns found sensitive**, as the [principle](ARCHITECTURE.md#principles) says:
of such a column, its range and the values of its enumeration are none in the profile, nor the range
and the values of the enumeration of the values of its lists, and the samples stay in the workspace;
its sentinels are no values of it, and are there whatever its sensitivity.

**Nothing given by hand.** The overrides fill no field. The names given, and the descriptions given
of the database, its tables and its entities, are laid over the profile by the stages that read it,
and never written to it; their fields are none in a profile written. A description given of a column
is laid over the same way, in place of the one proposed, which the profile keeps. What `scan` takes
of them - the marks, the sentinels, the primary keys and the discriminators - it writes as what the
table was counted with.

## Which stage fills what

Every attribute of a profile is filled by one step, as the
[principle](ARCHITECTURE.md#principles) says:

| Step | Fills |
|---|---|
| `scan` | the run and the semantic types of the profile; the rows, run, keys, primary key, column groups, column dependencies and discriminator of each table; the type, statistics, matches, separator of lists and the values of its lists, values, mark and sentinels of each column, the last two as the overrides give them |
| `relate` | the references and reference candidates of each table |
| `describe`, splitting the names | the terms of the names of the tables and columns |
| `describe`, proposing concepts | the glossary |
| `describe`, reading the names | the readings of the names |
| `describe`, describing the columns | the descriptions of the columns |

A table `scan` counts anew keeps the terms and readings of its name and of the names of its columns,
and the descriptions of its columns, but has no references, nor has any table a reference to the
tables dropped, until `relate` runs again.

**How `scan` updates a profile.** A scan writes the profile after every table. It updates the
profile there is: the tables no longer selected are dropped, the others kept until they are counted
anew. A scan that failed or was interrupted is resumed by the next, which skips the tables its run
counted, each naming the run by when it started; once a run has counted every table, the next scan
begins a new one. A profile scanned with other semantic types keeps its tables without their
matches, values, ranges and discriminators, until they are counted anew. A profile that cannot be
read, or one of another schema, is refused and never overwritten: it may be the work of hours.

## Versions of the format

Both files begin with the version of the format of the profile, as the reference below gives it: a
major and a minor part, written as text. A profile of an older minor version is read as it is, what
it lacks taken by its defaults; one of a newer minor version is refused, as the tool is older than
the profile. A profile of another major version is removed and scanned again, not converted. When
each part is raised is said in the module docs of `data_profiler.documents`.

## An example

The example profile of the simulation environment, `simulation/profiles/crm`, from which the test
data are generated - written by hand, so that it holds no glossary, terms or descriptions. Its
`profile.yml`:

<!-- begin file: simulation/profiles/crm/profile.yml -->
```yaml
# An example profile in the manner of a CRM: customers, their addresses and contacts, products,
# orders and their items, and its business partners - customers, suppliers, prospects and employees
# in one table, told apart by their kind -, under the abbreviated names such a system has; its texts
# of a semantic type have their match, by which they are generated, and its tables their keys - the
# items of an order of two columns, the order and the position -, and the references of their
# columns to the keys of others, each table in a file of its own in `tables/`. Its keys of whole
# numbers are numbered from one, sharing their values, but those of the products; contacts and
# addresses have keys of UUIDs as well, of the type `uuid` and as text, which orders refer to.
# It is loaded into the simulation environment by `uv run simulation load simulation/profiles/crm`.
format: '14.4'
catalog: crm
schema: sales
```
<!-- end file: simulation/profiles/crm/profile.yml -->

and the file of its orders, `tables/ord.yml`, with keys, references, a column group and a column
dependency:

<!-- begin file: simulation/profiles/crm/tables/ord.yml -->
```yaml
format: '14.4'
name: ord
rows: 20000
columns:
- name: ord_id
  type: bigint
  statistics:
    nulls: 0
    distinct: 20000
    range: {smallest: '1', largest: '20000'}
- name: ord_no
  type: varchar(14)
  statistics: {nulls: 0, distinct: 20000, lengths: {shortest: 14, longest: 14}}
- {name: cust_id, type: bigint, statistics: {nulls: 0, distinct: 4300}}
- name: cust_nm
  type: varchar(80)
  statistics: {nulls: 0, distinct: 3800, lengths: {shortest: 5, longest: 40}}
- name: cntct_uuid
  type: uuid
  statistics: {nulls: 8000, distinct: 3000}
  matches: [{type: uuid, sample: 1.0, table: 1.0}]
- {name: ord_dt, type: date, statistics: {nulls: 0, distinct: 2900}}
- name: ord_sts_cd
  type: varchar(3)
  statistics: {nulls: 0, distinct: 6, lengths: {shortest: 2, longest: 3}}
- {name: tot_amt, type: "decimal(14,2)", statistics: {nulls: 0, distinct: 15500}}
- name: curr_cd
  type: varchar(3)
  statistics: {nulls: 0, distinct: 3, lengths: {shortest: 3, longest: 3}}
  matches: [{type: currency-code, sample: 1.0, table: 1.0}]
- name: dlvr_dt
  type: date
  statistics: {nulls: 1900, distinct: 2800, sentinels: [{value: '9999-12-31', rows: 300}]}
- name: dlvr_strt_nm
  type: varchar(60)
  statistics: {nulls: 12350, distinct: 3000, lengths: {shortest: 4, longest: 38}}
- name: dlvr_pst_cd
  type: varchar(10)
  statistics:
    nulls: 0
    distinct: 1800
    lengths: {shortest: 5, longest: 5}
    sentinels: [{value: '', rows: 12400}]
  matches: [{type: postal-code, sample: 1.0, table: 1.0}]
- name: dlvr_cty_nm
  type: varchar(60)
  statistics: {nulls: 12420, distinct: 1400, lengths: {shortest: 3, longest: 28}}
- name: pymt_mthd_cd
  type: varchar(4)
  statistics: {nulls: 40, distinct: 5, lengths: {shortest: 2, longest: 4}}
- name: pymt_ref_id
  type: varchar(36)
  statistics: {nulls: 40, distinct: 19960, lengths: {shortest: 36, longest: 36}}
  matches: [{type: uuid, sample: 1.0, table: 1.0}]
- name: crd_no
  type: varchar(19)
  statistics: {nulls: 14000, distinct: 5700, lengths: {shortest: 16, longest: 19}}
  matches: [{type: card-number, sample: 1.0, table: 1.0}]
- name: iban
  type: varchar(34)
  statistics: {nulls: 16000, distinct: 3600, lengths: {shortest: 22, longest: 22}}
  matches: [{type: iban, sample: 1.0, table: 1.0}]
- name: dlvr_addr_guid
  type: varchar(36)
  statistics: {nulls: 12000, distinct: 3000, lengths: {shortest: 36, longest: 36}}
  matches: [{type: uuid, sample: 1.0, table: 1.0}]
keys: [[ord_id], [ord_no]]
primary_key: {columns: [ord_id]}
references:
- {column: cust_id, table: cust, key: cust_id, coverage: 0.98}
- {column: cntct_uuid, table: cntct, key: cntct_uuid, coverage: null}
- {column: dlvr_addr_guid, table: cust_addr, key: addr_guid, coverage: null}
column_groups:
- {columns: [dlvr_strt_nm, dlvr_pst_cd, dlvr_cty_nm], coherence: 0.994}
column_dependencies:
- {determinants: [cust_id], dependents: [cust_nm], strictness: 1.0}
```
<!-- end file: simulation/profiles/crm/tables/ord.yml -->

## Reference of the fields

Every field of both files, generated from the classes the tool reads and writes them by, with the
descriptions of their doc comments, by `scripts/generate.py`; it is never edited by hand. A field of
the default *absent* is left out where it holds nothing - its description says *None* -, and a
field of the default *empty* where it holds no entries. A map is written as the keys its
description names, each with its value; a list of classes as a list of maps.

<!-- begin reference: profile.yml -->
### `profile.yml`

The document begins with `format: "14.4"`, its version.

What `profile.yml` holds: the profile but its tables, whose matches name its types.

| Field | Type | Default | Description |
|---|---|---|---|
| `catalog` | text | required | The catalog of the schema, as Trino names the database it reads. |
| `schema` | text | required | The schema whose tables the profile describes. |
| `run` | [Run](#run) | absent | The last run of scan, or None where no scan wrote the profile. |
| `glossary` | map of [Concept](#concept) | empty | The concepts of the names of the tables and columns, by their words, once proposed. |
| `types` | map of [Definition](#definition) | empty | The semantic types of the project the tables were scanned with, beside those of the tool, by their names. |
| `description` | text | absent | What the database holds, given by hand, by an override; None in a profile written. |

#### Run

A run of the stage scan over the selected tables of a profile, which may take several scans.

A scan begins a run, and a run that did not finish, failing at a table or interrupted, is
resumed by the next scan; it finishes once every selected table is counted.

| Field | Type | Default | Description |
|---|---|---|---|
| `started` | timestamp | required | When it started, in UTC; it tells the run apart, and names it in the tables it counted. |
| `finished` | timestamp | absent | When it had counted every selected table, or None while it has not. |

#### Concept

An entry of the glossary: what a word means, and the terms it is written as in the names.

An abbreviation may be of several concepts, which a term of a name may each stand for.

| Field | Type | Default | Description |
|---|---|---|---|
| `abbreviations` | list of text | empty | The terms it is written as beside its word, in lower case, none where none is given; its word is a term of it where it is one term - `iban` -, and a word of several terms - `contact_person` - is written as its abbreviations alone. |
| `description` | text | absent | What it means, in English; None where none is given. |
| `omitted` | boolean | `false` | Whether it is left out of harmonized names, as a prefix that marks a custom column, which says nothing of what the column holds. |

#### Definition

A semantic type of a project, as a document gives it under its name.

Its name is of lower case letters, digits and `-`, beginning with a letter or a digit, and of no
type of the tool.

| Field | Type | Default | Description |
|---|---|---|---|
| `pattern` | text | required | The regular expression every value of the type matches whole. It is read by Python and by the database alike, so that it uses what both share: classes, repetitions, groups and alternatives, and no other escapes than of a character. |
| `sensitivity` | `none`, `personal` or `payment-card` | required | The rules the values of the type fall under. |
<!-- end reference: profile.yml -->

<!-- begin reference: tables/<table>.yml -->
### `tables/<table>.yml`

The document begins with `format: "14.4"`, its version.

A table of the schema, under its original name, and what was found about it.

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | text | required | The name of the table in the database. |
| `run` | timestamp | absent | When the run of scan that counted the table started, or None where no scan did. |
| `rows` | integer | required | The number of its rows, counted exactly. |
| `columns` | list of [Column](#column) | required | Its columns, in the order of the table. |
| `keys` | list of list of text | empty | Its keys: the columns, one or two, whose values together identify each of its rows, verified on the whole table, none of them a key of fewer columns; the fewer columns first, each in the order of the table. |
| `primary_key` | [PrimaryKey](#primarykey) | absent | What identifies its rows in a data model, a key chosen among its keys or the columns given; None where it has none. |
| `references` | list of [Reference](#reference) | empty | The references of its columns, one of each column at most, in the order of the columns. |
| `reference_candidates` | list of [Reference](#reference) | empty | The references of its columns of which several keys may be the one referred to, none of them preferred: those of a column after each other, in the order they are ranked, the columns in their order. |
| `column_groups` | list of [ColumnGroup](#columngroup) | empty | The column groups of its columns filled together, in the order of their first columns; a column is in one group at most. |
| `column_dependencies` | list of [ColumnDependency](#columndependency) | empty | The column dependencies of its columns, in the order of their determinants; a column is a determinant of one dependency at most. |
| `discriminator` | [Discriminator](#discriminator) | absent | The column whose values tell the entities of its rows apart, with those entities; None where no column does, or the overrides give it none. |
| `terms` | list of [Term](#term) | absent | The terms of its name, in their order, or None where it is not split yet. |
| `reading` | list of text | absent | The reading of its name: the word of the concept each of its terms stands for, at its place, the digits of a term of digits; None where it is not read. |
| `name_given` | text | absent | The harmonized name given by hand, by an override, in place of the one composed from its reading; None where none is given, and in a profile written. |
| `description` | text | absent | What the table holds, in English, given by hand, by an override; None where none is given, and in a profile written. |

#### Column

A column of a table, under its original name and type, and what was found about it.

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | text | required | The name of the column in the database. |
| `type` | text | required | The type of the column as the database names it, such as `varchar(40)`. |
| `statistics` | [Statistics](#statistics) | required | What is counted of the column. |
| `matches` | list of [Match](#match) | empty | The semantic types found in the column, the most frequent first. |
| `list_separator` | text | absent | The separator of the values of the lists its texts are, or None where they are none. |
| `items` | [Findings](#findings) | absent | The values of its lists, counted as those of a column are, or None where its texts are no lists. |
| `values` | list of [Value](#value) | empty | The values of the column, if it is an enumeration of no sensitivity, the most frequent first; none else. |
| `marked` | `none`, `personal` or `payment-card` | absent | The sensitivity of the column given by hand, by an override, or None where none is given. |
| `sentinels` | list of text | absent | The sentinels given by hand, by an override, as values, in place of those of the tool, that the column was counted with; None where none are given, and where the column has no text, which is counted without sentinels, whatever is given. |
| `terms` | list of [Term](#term) | absent | The terms of its name, in their order, or None where it is not split yet. |
| `reading` | list of text | absent | The reading of its name: the word of the concept each of its terms stands for, at its place, the digits of a term of digits; None where it is not read. |
| `description` | text | absent | What the column holds, in English, for a person who knows the business but not the database; None where it is not described. |
| `name_given` | text | absent | The harmonized name given by hand, by an override, in place of the one composed from its reading; None where none is given, and in a profile written. |

#### PrimaryKey

The key that identifies the rows of a table in a data model: chosen, or given by hand.

| Field | Type | Default | Description |
|---|---|---|---|
| `columns` | list of text | required | The names of its columns, in the order of the table. |
| `given` | boolean | `false` | Whether the overrides gave it, rather than it was chosen among the keys; one given may be none of them: its values not unique, or holding a key of fewer columns. |

#### Reference

A column of a table whose values are among those of a key of one column of a table.

The table referred to may be the one of the column, as a hierarchy refers to itself. Whether a
row or many refer to one of the key, the keys of the table of the column tell: one, where the
column is a key of it, else many.

| Field | Type | Default | Description |
|---|---|---|---|
| `column` | text | required | The name of the column that refers. |
| `table` | text | required | The name of the table referred to. |
| `key` | text | required | The name of its column of the key referred to. |
| `coverage` | number or `null` | required | The share of the values of the column, nulls and sentinels aside, found in the key, counted on the whole table; None of unmistakable values, such as UUIDs, which are equal to those of another column by no chance, so that a few found tell where they come from. |
| `given` | boolean | `false` | Whether the overrides gave it, rather than it was found. |

#### ColumnGroup

Columns of a table filled together: in mostly the same rows of its sample.

A column is filled in a row where it holds a value, neither null nor a sentinel. A group holds
its columns, and a column does not name its group, so that it is said in one place.

| Field | Type | Default | Description |
|---|---|---|---|
| `columns` | list of text | required | The names of its columns, at least two, in the order of the table. |
| `coherence` | number | required | The mean of the Jaccard indexes of the rows each two of its columns are filled in, from 0 to 1, with three digits. |

#### ColumnDependency

Columns of a table whose values follow from the value of another, its determinant.

Each value of the determinant comes with one value of each dependent, in the rows it is filled
in, neither null nor a sentinel; a null of a dependent there is a value as any other. Columns
that follow from each other are equivalent determinants, such as a code and its name, held
together. A dependency is found over the whole table, not within its entities, and as found:
one that follows from another, by a dependent of it, is held as well.

| Field | Type | Default | Description |
|---|---|---|---|
| `determinants` | list of text | required | Its determinant, then the columns equivalent to it, in the order of the table. |
| `dependents` | list of text | required | The columns that follow from it, in the order of the table; none where its determinants alone follow from each other. |
| `strictness` | number | required | How strictly it holds, from 0 to 1, with three digits: of the values of the determinant, the share of those that come with one value of the others, as their distinct values together count it, the least of each determinant. |

#### Discriminator

The column whose values tell the entities of a table apart, and those entities.

The rows of the table whose discriminator is null or a sentinel are of no entity.

| Field | Type | Default | Description |
|---|---|---|---|
| `column` | text | required | The name of the column, an enumeration of no sensitivity. |
| `entities` | list of [Entity](#entity) | required | Its entities, the one of the most rows first, at least two where it is found rather than given, and none where it is given of a column that holds no value the profile holds; a value is of one entity at most. |
| `given` | list of list of text | absent | The values of each entity the overrides gave, in their order, that it was counted with; None where it was found, none given. |

#### Term

A term of a name, as the vocabulary splits it, with the concepts it may stand for.

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | text | required | The term, in lower case. |
| `concepts` | list of text | empty | The words of the concepts written as it, its candidates, in the order of the glossary when it was split; none of a term of digits, which stands for itself, or of a term of no concept. |

#### Statistics

What is counted of a column on the whole table, its sentinels aside but where counted.

| Field | Type | Default | Description |
|---|---|---|---|
| `nulls` | integer | required | The number of nulls. |
| `distinct` | integer | required | The number of distinct values, approximate, as `approx_distinct` counts them. |
| `lengths` | [Lengths](#lengths) | absent | The range of the lengths of the values, or None where none was counted: for a column that holds no text, or only nulls and sentinels. |
| `range` | [Range](#range) | absent | The range of the values, or None where none is known: for a column whose values have no order, that holds only nulls and sentinels, or that is of a sensitivity. |
| `sentinels` | list of [Value](#value) | empty | The values that stand for no value found in the column, its sentinels, each with the rows that hold it, the most frequent first; none of a column whose values the database writes as no text. They are no values of the column, and shown whatever its sensitivity: the sentinels of the tool are fixed, those given are of the overrides. |

#### Match

A semantic type found in a column, with the share of its values that are of it.

| Field | Type | Default | Description |
|---|---|---|---|
| `type` | text | required | The semantic type, by its name: of the tool, or of the project. |
| `sample` | number | required | The share of the values of the sample, nulls and sentinels aside, that are of the type, from 0 to 1. |
| `table` | number | absent | The share of the values of the whole table, nulls and sentinels aside, that the pattern of the detector of the type matches, from 0 to 1, or None where it was not verified. Where the detector checks a value by more than its pattern, it is at least the share the check would give; a condition of the column is judged on the sample alone. |

#### Findings

What was found of the values of the lists of a column: statistics, types and enumeration.

| Field | Type | Default | Description |
|---|---|---|---|
| `statistics` | [Statistics](#statistics) | required | What is counted of the values, of the whole table: no nulls, as a list holds none. |
| `matches` | list of [Match](#match) | empty | The semantic types found in the values, the most frequent first. |
| `values` | list of [Value](#value) | empty | The values, if they are an enumeration of no sensitivity, the most frequent first; none else. |

#### Value

A value of an enumeration, or a sentinel, as text, with the rows that hold it.

| Field | Type | Default | Description |
|---|---|---|---|
| `value` | text | required | The value. |
| `rows` | integer | required | The number of the rows that hold it. |

#### Entity

The rows of a table of one entity of the business: those of some values of its discriminator.

| Field | Type | Default | Description |
|---|---|---|---|
| `values` | list of text | required | The values of the discriminator its rows hold, as text, the most frequent first. |
| `rows` | integer | required | The number of its rows. |
| `filled` | map of integer | required | The number of its rows each column of the table is filled in - holds a value, neither null nor a sentinel -, by the name of the column, of every column of the table in its order. |
| `name_given` | text | absent | Its harmonized name given by hand, by an override; None where none is given, and in a profile written. |
| `description` | text | absent | What it holds, in English, given by hand, by an override; None where none is given, and in a profile written. |

#### Lengths

The range of the lengths of the values of a text column.

| Field | Type | Default | Description |
|---|---|---|---|
| `shortest` | integer | required | The length of the shortest value, in characters. |
| `longest` | integer | required | The length of the longest value, in characters. |

#### Range

The smallest and the largest value of a column, as text.

| Field | Type | Default | Description |
|---|---|---|---|
| `smallest` | text or `null` | required | The smallest value, or None where it is withheld, as of a sensitive type. |
| `largest` | text or `null` | required | The largest value, or None where it is withheld, as of a sensitive type. |
<!-- end reference: tables/<table>.yml -->
