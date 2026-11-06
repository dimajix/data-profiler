# Projects and overrides

What the developer of a project writes: the configuration `project.yml`, which names the tables to
profile and the environments the database is profiled in, and the overrides `overrides.yml`, which
give by hand what the profiles of all environments take as given. This document says what holds
for both, shows a recipe for each task, and ends with the reference of every field, generated from
the classes the tool reads them by. What the profile holds is described in [PROFILE.md](PROFILE.md).

## The directory of a project

A project is a directory - `examples/crm/` is one, for the simulation environment:

| File | What it holds | Committed |
|---|---|---|
| `project.yml` | the configuration: the tables, the semantic types of the project, the language model, the environments | yes |
| `.env` | the variables of the project: the passwords, the users where they differ from one person to the next, what reaches the database | never |
| `overrides.yml` | what is given by hand, the same for all environments; optional | yes |
| `<environment>/` | the results of an environment, in a directory named after it: `profile/`, `workspace/` and `report.html` | the profile and the report may be; the workspace keeps itself out |

Every command names the environment it runs on, and the project by `--project`, else the current
directory: `uv run data-profiler scan simulation --project examples/crm`.

## The configuration: `project.yml`

*   **`tables`** selects the tables of the whole project, the same in every environment: a regular
    expression their names match whole, or a list of their names.
*   **`environments`** names each environment - lower case letters, digits, `-` and `_`, as it
    names its directory and is an argument of the command line - by the URL of its schema,
    `trino://host:port/catalog/schema`, and the user and the password it is reached as.
*   **`llm`** names the language model of Ollama that `describe` asks, as Ollama names it; it is
    pulled into Ollama once. A project without one runs `describe` only with `--without-llm`.
*   **`types`** gives semantic types of the project, beside those of the tool, each by a pattern its
    values match whole and its sensitivity. The profile holds them, so that it is read without its
    project.

**Variables.** A value `${NAME}` is taken from the variable `NAME`, as the whole value, never a part
of it. The password is given only so, never written out, so that `project.yml` can be committed and
shared. The variables are those of the process, completed by the `.env` of the project, which does
not override what the process sets - a `no_proxy` the shell sets, for one, has to name the database
itself. They are resolved when an environment is used, so that an environment runs without the
variables of the others, and `report` without its own. The `.env` holds what reaches the database
as well: `REQUESTS_CA_BUNDLE`, the certificate of a CA of one's own, and `NO_PROXY`, for a database
no proxy reaches.

**Ollama** is a matter of the machine, not of the project: it answers where the variable
`OLLAMA_HOST` says, `[scheme://]host[:port]` of the scheme `http` or `https`, else at
`http://localhost:11434`. The tool reaches it
past every proxy, as its prompts hold values of the database.

## The overrides: `overrides.yml`

A proposal of the tool - a concept, a reading, a description, a key, a reference - that is wrong is
corrected in `overrides.yml`, not in the profile, where the next run of a stage would replace it.
The overrides are the same for all environments of a project, and laid over every profile of it.
Tables and columns are named by their original names, concepts by their words, entities by their
harmonized names, all as keys, so that a person writes no more than what is given.

**Each override is taken by the stage whose work it is**, and counts once that stage has run again:

| What is given | Taken by | Counts |
|---|---|---|
| the sensitivity of a column | `scan`, and every stage that reads the profile | at once: a column marked sensitive shows no values without a scan again; a mark taken out gives back values once `scan` counts the column again |
| the sentinels of a column | `scan`, which counts the column with them | once `scan` counts the table again |
| the primary key of a table | `scan`, which takes it whether or not its values are unique, and warns where they are not | once `scan` counts the table again |
| a column that determines none, `determines: false` | `scan`, which looks for no dependency of it; the stages that read the profile drop those found of it | at once; the dependencies of the columns equivalent to it once `scan` counts the table again |
| the discriminator of a table, or none | `scan`, which counts the entities by it | once `scan` counts the table again |
| the names and descriptions of entities | the stages that read the profile | where the discriminator was counted with the values given |
| the reference of a column, or none | `relate`, which does not search it but measures it, and warns where its coverage is below what a reference is found at | once `relate` relates the tables again |
| concepts of the glossary | `describe`, which splits and reads the names by them, and `report` | at the next `describe`; the language model is asked of no term of a concept given |
| the reading of a name | `describe` and `report` | once `describe` has split the name, as a reading agrees with the terms of its name |
| the harmonized name of a table or column | `report` | at once; it comes before the name composed from the reading, and so resolves a collision of two names |
| the description of the database, a table or a column | `describe`, which shows the first two to the language model with every question of them and asks for no column described, and `report` | at once |

A scan resumed counts again the tables the overrides now give otherwise: the marks or the sentinels
of their columns, a column that determines none, their primary keys or their discriminators.

**A concept given comes before those proposed.** It takes the place of the concept proposed of its
word, keeping only the abbreviations proposed beside those given; the terms it is written as are
taken from the other concepts proposed, so that a term given stands for the concepts given alone.
A term that is the word of another concept stays a term of that concept as well, and the reading of
a name tells which of them it stands for.

**What is refused, and what is warned of.** An override that names what is not profiled, or cannot
be what it gives, is refused, naming it:

*   `scan` refuses a table the project does not select before it counts anything; once it has
    counted a table, a column the table does not have, sentinels of a column whose values the
    database writes as no text, a primary key of no columns or of one twice, and a discriminator of
    a column marked of a sensitivity, of entities of no values, or of a value twice. The tables
    before it stay in the profile, as after any failure of a scan.
*   `relate` refuses a table or column the profile does not have, and a reference to one or of a
    column to itself, before it queries anything.
*   The stages that read the profile refuse a table or column it does not have, a reading that is
    no reading of the terms of its name - of another number of words, or a word of no concept of
    the term at its place -, a name other than in snake_case, that of an entity among them, and a
    discriminator as `scan` does.

As the overrides are the same for all environments, whose tables may differ, the stages warn, and
go on, of an abbreviation no name of the profile has, of values of a discriminator a table does not
hold, of a primary key whose values are not unique, of a reference whose coverage is below what a
reference is found at or to a column that is no key of one column, and of a discriminator or a
reference given otherwise than the profile was counted or related with.

## Recipes

Each recipe is a snippet of `project.yml` or `overrides.yml`, as it stands in the file; the
snippets of the overrides name the tables of the example profile `simulation/profiles/crm`.
`tests/test_recipes.py` reads every snippet - the line `format:` left out, which the file has
first - and lays those of the overrides over that profile as the stages that read it do, so that a
recipe that names what the profile does not have, or gives a reading of no terms of its name, fails
the tests.

### Select tables

By a list of their names:

```yaml project.yml
tables: [cust, cust_addr, ord, ord_itm]
environments:
  dev:
    url: trino://starburst.example.com:443/crm/sales
    user: ${CRM_USER}
    password: ${CRM_PASSWORD}
```

Or by a regular expression, matched against the whole name:

```yaml project.yml
# Every table but those of the staging area, which begin with stg_.
tables: (?!stg_).*
environments:
  dev:
    url: trino://starburst.example.com:443/crm/sales
    user: ${CRM_USER}
    password: ${CRM_PASSWORD}
```

### Profile the database in several environments

Each environment keeps its results in a directory of its own, named after it. The URLs may be
written out, as here, or taken from variables as well:

```yaml project.yml
tables: .*
llm: qwen3.5:2b
environments:
  dev:
    url: trino://starburst-dev.example.com:443/crm/sales
    # The user differs from one person to the next: each sets it in the .env.
    user: ${CRM_USER}
    password: ${CRM_DEV_PASSWORD}
  prod:
    url: trino://starburst.example.com:443/crm/sales
    # A technical user, the same for everyone.
    user: profiler
    password: ${CRM_PROD_PASSWORD}
```

### Recognise a semantic type of the project

A value of an account number of this database alone - an `A` and ten digits - is recognised by a
pattern; the pattern is read by Python and by the database alike, so that it uses what both share:
classes, repetitions, groups and alternatives, and no other escapes than of a character.

```yaml project.yml
tables: .*
environments:
  dev:
    url: trino://starburst.example.com:443/crm/sales
    user: ${CRM_USER}
    password: ${CRM_PASSWORD}
types:
  account-number:
    pattern: "A[0-9]{10}"
    sensitivity: personal
```

### Describe the database and a table

The language model is shown both with every question of them, and the report shows them:

```yaml overrides.yml
description: >-
  The CRM of a wholesaler of office supplies: its customers, mostly companies, their contacts and
  addresses, the products it sells, and the orders of its customers.
tables:
  ord_itm:
    description: The positions of an order, one product each, with its quantity and price.
```

### Mark a column the detectors miss

No detector recognises the names of persons. A column marked sensitive shows no values in the
profile, the report or the prompts of the language model; `sensitivity: none` takes the mark of a
detector back, where it found a sensitive type that is none.

```yaml overrides.yml
tables:
  cntct:
    columns:
      frst_nm: {sensitivity: personal}
      lst_nm: {sensitivity: personal}
```

### Give the sentinels of a column

The values that stand for no value in a column are counted apart and left aside, as nulls are. The
tool brings sentinels of its own, of the columns whose values the database writes as text; those
given take their place, and `sentinels: []` gives none.

```yaml overrides.yml
tables:
  ord:
    columns:
      # Empty where no delivery address is given; zeros, where a system writes them for none.
      dlvr_pst_cd: {sentinels: ["", "00000"]}
```

### Give concepts of the glossary

A concept is a word, from which the harmonized names are composed, the abbreviations it is written
as in the names, and a description, from which the language model describes the columns. Its word
is a term of it, where it is one term; a word alone is given as `{}`.

```yaml overrides.yml
glossary:
  customer:
    abbreviations: [cust]
    description: A person or company that buys from the company, with its orders and addresses.
  address:
    # Written in two ways in the names.
    abbreviations: [addr, adr]
    description: Where a person or company is reached, by post or by e-mail.
  # A word alone: `iban` is a term of it.
  iban: {}
```

### Leave a prefix out of the names

A prefix that marks a custom column says nothing of what the column holds; its concept is omitted
from the harmonized names:

```yaml overrides.yml
glossary:
  airplus:
    abbreviations: [ap]
    description: Marks a column added to the CRM for AirPlus; it says nothing of what it holds.
    omitted: true
```

### Read a name whose term stands for several concepts

Where a term is an abbreviation of several concepts, the language model chooses the one it stands
for in each name; the reading of a name gives it by hand, a word for each term at its place. Here
`ap` is the prefix of a custom column and a contact person in one name, `ap_ap_nm`:

```yaml overrides.yml
glossary:
  airplus:
    abbreviations: [ap]
    omitted: true
  contact_person:
    abbreviations: [ap]
    description: The person a customer is reached through, one of its contacts.
  name:
    abbreviations: [nm]
tables:
  cust:
    columns:
      ap_ap_nm: {reading: [airplus, contact_person, name]}
```

### Name and describe a column

A name given takes the place of the one composed from the reading, as where two columns of a table
would share one; a description given takes the place of the one the language model proposes, which
is then not asked for it.

```yaml overrides.yml
tables:
  cust:
    columns:
      cust_ap_id:
        name: contact_person_id
        description: The identifier of the contact person a customer is reached through.
```

### Give the primary key of a table

Of the keys found, the tool chooses the one of the fewest columns, then of the types a database
generates keys of; one given takes its place, whether or not its values are unique:

```yaml overrides.yml
tables:
  ord_itm:
    # The order and the position, in place of the identifier chosen.
    primary_key: [ord_id, pos_no]
```

### Give the reference of a column, or none

A column of whole numbers that a key numbered from one holds as well is a candidate of several
references; the reference given is measured, not searched. `reference: false` gives none, whatever
is found:

```yaml overrides.yml
tables:
  ord:
    columns:
      cust_id: {reference: {table: cust, column: cust_id}}
  prtnr:
    columns:
      # The number a business partner has as a customer in another system.
      cust_no: {reference: false}
```

### Give a column that determines no other

A dependency found that is none - the name of a product group follows from its code, but a name
identifies nothing - is dropped by giving the column as determining none:

```yaml overrides.yml
tables:
  ord_itm:
    columns:
      prodgrp_nm: {determines: false}
```

### Give the discriminator of a table and name its entities

A table that holds the rows of several entities - customers, suppliers and employees - tells them
apart by the values of one column. Each entity is given under its harmonized name, by one value at
least; the other values it is found of join it. `discriminator: false` gives none, whatever is
found.

```yaml overrides.yml
tables:
  prtnr:
    discriminator:
      column: prtnr_typ_cd
      entities:
        customer:
          values: [K]
          description: A company that buys from the company, with its credit limit and terms.
        supplier:
          values: [L]
          description: A company the company buys from, paid to its bank account.
        prospect: {values: [I]}
        employee: {values: [M]}
```

## Versions of the formats

Each file begins with the version of its format, as the reference below gives it: a major and a
minor part, written as text, `format: "4.0"`. A file of an older minor version is read as it is,
what it lacks taken by its defaults; one of a newer minor version is refused, as the tool is older
than the file, and one of another major version is refused as well, to be edited by hand to the new
version - the tool converts none. When each part is raised is said in the module docs of
`data_profiler.documents`.

## The example project

`examples/crm/` profiles the simulation environment, as the README says. Its files show each field
of the configuration and each kind of override:

<!-- begin file: examples/crm/project.yml -->
```yaml
# The example project: the tables of the example CRM, profiled in the simulation environment.
format: "4.0"
# The tables to profile: a regular expression matched whole, or a list of their names.
tables: .*
# The language model of Ollama the names are described by.
llm: qwen3.5:2b
# The environments, each by the URL of its schema, its user and its password; its results are kept
# in a directory named after it, here `simulation/`.
environments:
  simulation:
    url: trino://localhost:8443/crm/sales
    user: profiler
    # The password is given only by a variable, of the process or of the `.env` of the project.
    password: ${SIMULATION_PASSWORD}
```
<!-- end file: examples/crm/project.yml -->

<!-- begin file: examples/crm/overrides.yml -->
```yaml
# What is given by hand of the profiles of the example project, the same for all its environments;
# docs/PROJECT.md describes each kind of override, and when it counts.
format: "7.4"
# What the database holds: the language model is shown it with every question.
description: >-
  The CRM of a wholesaler of office supplies: its customers, mostly companies, their contacts and
  addresses, the products it sells, and the orders of its customers.
# The concepts of the glossary, each under its word, from which the harmonized names are composed.
glossary:
  customer:
    abbreviations: [cust]
    description: A person or company that buys from the company, with its orders and addresses.
  # Written in two ways in the names.
  address:
    abbreviations: [addr, adr]
    description: Where a person or company is reached, by post or by e-mail.
  # A prefix that marks a custom column, left out of the names.
  airplus:
    abbreviations: [ap]
    description: >-
      Marks a column added to the CRM for AirPlus, a custom column; it says nothing of what the
      column holds.
    omitted: true
  # Written as the prefix above is: the reading of a name tells which of the two `ap` stands for.
  contact_person:
    abbreviations: [ap]
    description: The person a customer is reached through, one of its contacts.
  identifier:
    abbreviations: [id]
  name:
    abbreviations: [nm]
  segment:
    abbreviations: [seg]
  code:
    abbreviations: [cd]
  # A word alone, which is a term of it.
  iban: {}
tables:
  cust:
    columns:
      # The names of persons, which no detector recognises.
      cust_nm: {sensitivity: personal}
      # Read, named and described by hand; its reference is one of several candidates, as keys
      # numbered from one share their values.
      cust_ap_id:
        reading: [customer, contact_person, identifier]
        name: contact_person_id
        description: The identifier of the contact person a customer is reached through.
        reference: {table: cntct, column: cntct_id}
      # Terms that stand for one concept or another, read by hand.
      ap_ap_nm: {sensitivity: personal, reading: [airplus, contact_person, name]}
      ap_seg_cd: {reading: [airplus, segment, code]}
  cntct:
    columns:
      frst_nm: {sensitivity: personal}
      lst_nm: {sensitivity: personal}
  ord:
    columns:
      # The customer of an order, one of several candidates, as for cust_ap_id.
      cust_id: {reference: {table: cust, column: cust_id}}
      # Postal codes of a delivery: empty where none is given; zeros, where a system writes them.
      dlvr_pst_cd: {sentinels: ["", "00000"]}
  ord_itm:
    description: The positions of an order, one product each, with its quantity and price.
    # The order and the position, in place of the identifier chosen.
    primary_key: [ord_id, pos_no]
    columns:
      # Found to determine others, as it follows from the code of the group, but a name
      # identifies nothing.
      prodgrp_nm: {determines: false}
  prtnr:
    columns:
      # The number a business partner has as a customer elsewhere: no reference, whatever is found.
      cust_no: {reference: false}
    # The business partners of four kinds, each entity named by one value; the others it is found
    # of join it.
    discriminator:
      column: prtnr_typ_cd
      entities:
        customer:
          values: [K]
          description: A company that buys from the company, with its credit limit and terms.
        supplier:
          values: [L]
          description: A company the company buys from, paid to its bank account.
        prospect: {values: [I]}
        employee: {values: [M]}
```
<!-- end file: examples/crm/overrides.yml -->

## Reference of the fields

Every field of both files, generated from the classes the tool reads them by, with the descriptions
of their doc comments, by `scripts/generate.py`; it is never edited by hand. A field of the default
*absent* is left out where nothing is given of it - its description says *None* -, and one of the
default *empty* where it holds no entries; *False* is written `false`. A map is written as the keys
its description names, each with its value.

<!-- begin reference: project.yml -->
### `project.yml`

The document begins with `format: "4.0"`, its version.

The configuration of a project, as its file holds it.

| Field | Type | Default | Description |
|---|---|---|---|
| `tables` | text or list of text | required | The tables to profile, of the whole project: a regular expression their names match whole, or a list of their names. |
| `environments` | map of [Settings](#settings) | required | The environments the database is profiled in, by their names - lower case letters, digits, `-` and `_`, beginning with a letter or a digit -, which name the directories of their results. |
| `llm` | text | absent | The language model of Ollama that `describe` asks, as Ollama names it, or None where the project names none, so that `describe` runs only with `--without-llm`. |
| `types` | map of [Definition](#definition) | empty | The semantic types of the project, beside those of the tool, by their names. |

#### Settings

How an environment is reached, as the configuration gives it: values or `${NAME}`.

| Field | Type | Default | Description |
|---|---|---|---|
| `url` | text | required | The schema the environment profiles, `trino://host:port/catalog/schema`, or `${NAME}`, the variable that holds it. |
| `user` | text | required | The user the environment is reached as, or `${NAME}`, the variable that holds it. |
| `password` | text | required | `${NAME}`, the variable that holds the password of the user; never the password itself. |

#### Definition

A semantic type of a project, as a document gives it under its name.

Its name is of lower case letters, digits and `-`, beginning with a letter or a digit, and of no
type of the tool.

| Field | Type | Default | Description |
|---|---|---|---|
| `pattern` | text | required | The regular expression every value of the type matches whole. It is read by Python and by the database alike, so that it uses what both share: classes, repetitions, groups and alternatives, and no other escapes than of a character. |
| `sensitivity` | `none`, `personal` or `payment-card` | required | The rules the values of the type fall under. |
<!-- end reference: project.yml -->

<!-- begin reference: overrides.yml -->
### `overrides.yml`

The document begins with `format: "7.4"`, its version.

What is given by hand of a profile: concepts, names, descriptions, columns, discriminators.

| Field | Type | Default | Description |
|---|---|---|---|
| `description` | text | absent | What the database holds, or None where it is not given. |
| `glossary` | map of [Concept](#concept) | empty | The concepts given, by their words. |
| `tables` | map of [TableOverride](#tableoverride) | empty | What is given of each table, by its original name. |

#### Concept

An entry of the glossary: what a word means, and the terms it is written as in the names.

An abbreviation may be of several concepts, which a term of a name may each stand for.

| Field | Type | Default | Description |
|---|---|---|---|
| `abbreviations` | list of text | empty | The terms it is written as beside its word, in lower case, none where none is given; its word is a term of it where it is one term - `iban` -, and a word of several terms - `contact_person` - is written as its abbreviations alone. |
| `description` | text | absent | What it means, in English; None where none is given. |
| `omitted` | boolean | `false` | Whether it is left out of harmonized names, as a prefix that marks a custom column, which says nothing of what the column holds. |

#### TableOverride

What is given by hand of a table and its columns.

| Field | Type | Default | Description |
|---|---|---|---|
| `columns` | map of [ColumnOverride](#columnoverride) | empty | What is given of each column, by its original name. |
| `reading` | list of text | absent | The word of the concept each term of the name of the table stands for, in their order, or None where it is not given. |
| `name` | text | absent | The harmonized name of the table, in snake_case, in place of the one composed from its reading, or None where it is not given. |
| `description` | text | absent | What the table holds, or None where it is not given. |
| `discriminator` | [DiscriminatorOverride](#discriminatoroverride) or `false` | absent | The discriminator of its entities, or False where it has none, whatever is found; None where it is not given. |
| `primary_key` | list of text | absent | The columns of its primary key, in place of the one chosen among its keys, one at least and each once, or None where it is not given. |

#### ColumnOverride

What is given by hand of a column.

| Field | Type | Default | Description |
|---|---|---|---|
| `sensitivity` | `none`, `personal` or `payment-card` | absent | The sensitivity of the column, or None where it is not given. |
| `sentinels` | list of text | absent | The values that stand for no value in the column, in place of those of the tool, none where empty; None where they are not given. |
| `reading` | list of text | absent | The word of the concept each term of its name stands for, in their order, or None where it is not given. |
| `name` | text | absent | Its harmonized name, in snake_case, in place of the one composed from its reading, or None where it is not given. |
| `description` | text | absent | What it holds, in place of the description proposed, or None where it is not given. |
| `reference` | [ReferenceOverride](#referenceoverride) or `false` | absent | The key it refers to, or False where it refers to none, whatever is found; None where it is not given. |
| `determines` | `false` | absent | False where it determines no other column, whatever is found; None where it is not given. |

#### DiscriminatorOverride

The discriminator of a table given by hand, and its entities by their harmonized names.

| Field | Type | Default | Description |
|---|---|---|---|
| `column` | text | required | The name of the column whose values tell the entities apart, an enumeration of no sensitivity. |
| `entities` | map of [EntityOverride](#entityoverride) | empty | What is given of its entities, by their harmonized names, in snake_case; the values given of none join them, or are of entities found as `scan` finds them. |

#### ReferenceOverride

The key of one column a column refers to, given by hand.

| Field | Type | Default | Description |
|---|---|---|---|
| `table` | text | required | The name of the table referred to, of another or of the table of the column. |
| `column` | text | required | The name of its column of the key referred to. |

#### EntityOverride

What is given by hand of an entity of a table: its values, and what it holds.

| Field | Type | Default | Description |
|---|---|---|---|
| `values` | list of text | required | Values of the discriminator its rows hold, as text, one at least; the others it is found of join them. |
| `description` | text | absent | What it holds, or None where it is not given. |
<!-- end reference: overrides.yml -->
