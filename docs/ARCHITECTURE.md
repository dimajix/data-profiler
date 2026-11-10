# Architecture of data-profiler

This document draws the overall picture of the project - what the parts are, how they work
together, and the principles the design follows. Every section ends with the document that holds
the details, where there is one; the list at the end names them all.

data-profiler is a command line tool for data engineers that profiles the tables of an SQL
database - Trino and Starburst first - to help build an understandable data model of it: what each
column contains, and a harmonized name for it, composed from one glossary for the whole schema. It
reads the database through generated SQL, recognises the semantic types of columns with
deterministic detectors, and asks a small local language model for the concepts of the terms of
the names and for descriptions of the columns; no value leaves the machine it runs on.

The project is at its beginning: the parts below are the design it is built to, and come into the
code one by one.

## Parts

The tool is one Python package, `data_profiler`, in `src/`. The test data generator is a project of
its own, `simulation`, in `simulation/`: it uses the tool's profile and its detectors, but the tool
does not depend on it, nor on what it needs. Both are one uv workspace, with one lock file and one
environment.

*   **`data_profiler.profile`** - the profile: its classes and the version of their formats, read
    and written as a directory of documents, one of the schema and one of each table; the profile a
    scan starts from, in its run, resumed or new; and the form the semantic types of a project and
    the separator of lists take in a document, which `project` reads them in as well, and the
    overrides the separator.
*   **`data_profiler.overrides`** - the overrides of a project: read from its documents, merged, and
    laid over each table a scan counts and over a profile a stage reads, refused where they name
    what is not profiled or give what cannot be, and warned of where they give what a profile does
    not take, as [PROJECT.md](PROJECT.md#the-overrides-overridesyml-and-overrides) says; what a
    concept proposed adds to them, and a field of them set in the file it belongs to.
*   **`data_profiler.workspace`** - the workspace: the local directory of samples and intermediate
    results, which never leaves the machine; the samples and the enumerations of tables as
    Parquet.
*   **`data_profiler.project`** - the project: its configuration `project.yml` - the tables to
    profile, the semantic types of its own, the language model, and the environments, each by its
    URL, its user and its password, the password given by a variable -, its variables in `.env`,
    which complete those of the process, its overrides in `overrides.yml` and `overrides/`, and the
    directories of the results of each environment.
*   **`data_profiler.documents`** - documents: the YAML files a person reads and writes, those of
    the profile and the configuration of a project among them, each the fields of one class with
    the version of its format, of a major and a minor part, so that a document of an older minor
    version is read with the defaults of what it lacks; what is wrong with one is named, field by
    field. Several documents of a format are read merged into one, a field given in two of them
    refused; a field of them is set in the one that gives it, all else kept as a person wrote it.
*   **`data_profiler.files`** - files written whole or not at all, for documents and the
    workspace, under names every system takes - the names of tables among them.
*   **`data_profiler.source`** - the database: the `Source`, which `connect` makes from a URL, and
    the `Dialect`, which writes every SQL statement the tool sends. A source lists the tables and
    columns of its schema - their metadata - through its dialect, counts what a table holds in
    queries of `PER_QUERY` counts at most, the limit every query of counts keeps, and runs queries
    in that schema, so that another database brings only its connection and its SQL. Trino is
    reached by HTTPS as a user with a password, both given apart from the URL; certificates and
    proxies come from the variables of the process. A source `unnested` reads one of its tables as
    a row of each value of the lists of a column, so that what counts a column counts those values
    alike.
*   **`data_profiler.values`** - values of the database, as the tool takes them: a count as a
    number, any value as text, as the profile holds it.
*   **`data_profiler.statistics`** - the statistics of a table, counted by one query that it builds
    from the building blocks of the dialect, and whose row it reads back.
*   **`data_profiler.enumerations`** - the enumerations of a table, their values counted by one
    query built the same way.
*   **`data_profiler.lists`** - the columns of lists of a table: those whose texts are lists of
    values, by the separator of the project or of the table, found in its sample by `detect`, and
    the values of their lists, their items, counted, enumerated and matched by the modules that do
    so of a column, on a source `unnested`.
*   **`data_profiler.matching`** - the matches of a table: the semantic types of its columns,
    recognised in its sample by `detect`, and verified on the whole table by one query built the
    same way.
*   **`data_profiler.keys`** - the keys of a table: the columns whose values identify its rows,
    indicated by its statistics and its sample, and verified on the whole table by exact distinct
    counts in queries built the same way, and its primary key.
*   **`data_profiler.grouping`** - the column groups of a table: its columns filled together,
    found in its sample.
*   **`data_profiler.dependencies`** - the column dependencies of a table: its columns whose values
    follow from another, found in its sample, and verified on the whole table by exact distinct
    counts in queries built the same way.
*   **`data_profiler.entities`** - the entities of a table: its rows told apart by the values of
    its discriminator, counted by one query built the same way, and one more of each candidate of
    the values of lists, on a source `unnested`.
*   **`data_profiler.disclosure`** - what of the values of a table goes into the profile: the
    ranges and the values of enumerations of its columns of no sensitivity, and the values of their
    samples shown to the language model, whose answers go into it.
*   **`data_profiler.sampling`** - the sample of a table, taken at random by a query built the same
    way.
*   **`data_profiler.scan`** - the stage `scan`: statistics, enumerations, samples, detector
    matches, columns of lists and the values of their lists, keys, column groups, column
    dependencies and entities of the selected tables, written to the profile table by table.
*   **`data_profiler.references`** - the references between the tables of a profile: their columns
    whose values are those of a key, indicated by the profile, probed by values of each looked up in
    the whole key, and counted on the whole table by queries built the same way, the values staying
    in the database.
*   **`data_profiler.relate`** - the stage `relate`: the references and reference candidates of
    the tables of a profile, written to it.
*   **`data_profiler.detect`** - what the values of a column are - of which semantic type and
    sensitivity, or sentinels of no value -, and the detectors that recognise them.
*   **`data_profiler.currencies`** - the alphabetic codes, numbers and English names of the
    currencies of ISO 4217, current and withdrawn since the euro, of which `detect` makes the
    patterns of its types of currencies and the simulation their values.
*   **`data_profiler.countries`** - the codes of two and three letters, numbers and English names
    of the countries of ISO 3166, current and withdrawn, of which `detect` makes the patterns of its
    types of countries and the simulation their values.
*   **`data_profiler.glossary`** - splitting the original names of tables and columns into terms,
    those written together by the vocabulary of the profile, each with its candidates among the
    concepts of the glossary, which the profile holds, and composing harmonized names from the
    readings of the names.
*   **`data_profiler.llm`** - the language model: a prompt answered in the form of a JSON schema,
    by the `LanguageModel`; `Ollama` runs one locally, reached past every proxy.
*   **`data_profiler.describe`** - the stage `describe`: the names of the tables and columns split
    into their terms, by a step of its own without the language model, and read - by the one
    candidate of each term, else by the language model -; and the glossary's concepts and the
    columns' descriptions, proposed by the language model, asked by prompts rendered from Jinja2
    templates in `data_profiler/templates/prompts/`.
*   **`data_profiler.adopt`** - the stage `adopt`: a person asked about each concept a profile
    proposes, and the answers written to the overrides.
*   **`data_profiler.report`** - the stage `report`: the profile rendered as one HTML document,
    its styles inside and no script, from a Jinja2 template in `data_profiler/templates/`.
*   **`data_profiler.diagram`** - the layout of a table and the tables connected to it, in pixels,
    which the template of `report` draws.
*   **`data_profiler.cli`** - the command line: it reads the arguments, and runs the stages on an
    environment of a project through `commands`.
*   **`data_profiler.commands`** - the frame every command line of the project, the simulation's
    as well, runs its work in: it alone configures the log and ends the program, showing users
    what may be shown of an error.
*   **`simulation`** - test data: tables generated from a profile and loaded into the simulation
    environment - Trino, reached by HTTPS with a password as Starburst is, with a PostgreSQL
    catalog, and Ollama under a compose profile of its own -, for tests and for trying the tool
    without access to the real database. It creates the tables by Trino and fills them by `COPY` in
    the PostgreSQL behind the catalog, where Trino has named them in lower case.

The stages read and write the profile: `scan` uses `source`, `statistics`, `enumerations`,
`sampling`, `lists`, `matching`, `keys`, `grouping`, `dependencies`, `entities`, `overrides`,
`disclosure`, `values` and `workspace`, `relate` uses `source`, `overrides` and `references`, which
takes the terms of names from `glossary`, `describe` uses `glossary`, `overrides`, `llm`,
`disclosure`, `values` and `workspace`, `report` the profile and `overrides`, which it lays over it,
and `glossary` and `diagram` for its names and diagrams, and `adopt` reads the profile and writes
through `overrides`; `cli` runs the stages, gives the overrides to each but `adopt`, which reads
them anew for each concept, and the language model, made by `llm` as the project names it, to
`describe`, unless it is to ask none. The semantic types of a project and its separator of lists
reach `scan` from `project`, and every stage after it from the profile.

## The domain

*   **Project** - one database, profiled in environments: a directory of its configuration, which
    selects the tables, of its variables, which hold the passwords - and the users, where they
    differ from one person to the next - and are not shared, of its overrides, and of the results
    of each environment; described in [PROJECT.md](PROJECT.md).
*   **Environment** - one of the places the database of a project is found - dev, test, prod, or
    the simulation environment -, each a schema with a URL, a user and a password of its own; its
    results, a profile, a workspace and a report, are kept in a directory of its own, named after
    it.
*   **Stage** - one of `scan`, `relate`, `describe`, `adopt` and `report`: a step of the work that
    can be run on its own, from what the stages before it left. `adopt` alone writes the overrides,
    as a person answers, and never the profile.
*   **Run** - the counting of the selected tables of an environment, which may take several
    scans: a scan begins it, the next resumes it where it did not finish - failing at a table, or
    interrupted -, and it finishes once every selected table is counted. It is told apart by when
    it started, which each table it counted names.
*   **Source** - a schema of the database the tool reads, by its URL; **Dialect** - the SQL of
    one kind of database.
*   **Profile** - the documents describing the tables of one schema of a database: its tables and
    columns, what was found about them, the glossary, and the semantic types of its project; a
    directory of a document of the schema and a document of each table, so that a person reads a
    table in a file of its own. It is the only thing the stages hand to each other besides the
    workspace, and it holds no values of the columns found sensitive (see
    [Principles](#principles)); described in [PROFILE.md](PROFILE.md).
*   **Table** and **Column** - as found in the database, under their original names.
*   **Statistics** - what is counted of a column on the whole table: its nulls, each of its
    sentinels, the approximate number of its distinct values, the range of its values, the range
    of lengths of texts, the last three without the sentinels. The rows are counted once per table.
*   **Sentinel** - a value that stands for no value: an empty text, `NULL`, `N/A`, `-`, a day such
    as `9999-12-31`. It is of no semantic type, and left aside as a null is, but each is counted
    apart and named in the profile with its rows, whatever the sensitivity of its column, so that
    a person can check them: the sentinels of the tool are fixed texts, and those given are of the
    overrides. The tool brings its sentinels, of the columns whose values the database writes as
    text; an override gives those of a column in their place.
*   **Column of lists** - a column whose texts are lists of values, `12;47;3`, separated by the
    separator of lists the project gives, the same in all tables of the database, or an override of
    a table in its place; the tool guesses none. Nearly every text is a list, of one value or more,
    and one of more at least. Its texts are no values of a discriminator, the values of its lists
    are. The values of its lists are its **items**, counted as the values of a column are - their
    statistics, matches and enumeration -, on the whole table; a match of them of a sensitive type
    makes the column as sensitive, and they keep what the column keeps of a range and values.
*   **Enumeration** - a column with few distinct values, at most a threshold, of which not each is
    in one row alone; its values with the rows of each, its nulls and sentinels aside.
*   **Sample** - rows taken from a table at random, kept in the workspace.
*   **Semantic type** - what the values of a column are: a phone number, an IBAN, a date, a
    currency, a country. Each has a **sensitivity**: personal data (GDPR), payment card data (PCI),
    or none. The tool brings its types; a project gives types of its own, each by a pattern alone,
    which the profile holds, so that it is read without its project.
*   **Detector** - recognises one semantic type: by a pattern every value of the type matches - in
    the values of a sample, and on the whole table in SQL -, by a check of a value where the
    pattern does not say enough, such as a checksum, and by a condition of the column where no
    value says enough alone, judged on the values of a sample together. Its type is a match of a
    column where it recognises at least its threshold of the values of the sample.
*   **Match** - a semantic type found in a column, with the share of values that match it in the
    sample and, once verified, in the whole table. A column may be a match of several types - the
    numbers of countries and of their currencies, `276` -: each is reported, none preferred, and
    a person decides which it is, in modelling the data.
*   **Key** - columns of a table, one or two, whose values together identify each of its rows,
    verified on the whole table, none of them a key alone. As a table may have hundreds of columns,
    the keys are indicated first: by the approximate distinct counts of the statistics, which reach
    the rows, and by the sample, in which they are unique; few are verified, in few queries.
    The **primary key** is the one that identifies the rows in a data model: of the keys, the one of
    the fewest columns, then of the types a database generates keys of, then the first, unless an
    override gives it, which is taken whether or not its values are unique - warned of where they
    are not.
*   **Reference** - a column of a table whose values are among those of a key of one column of a
    table, of another or of the same, as a hierarchy refers to itself, with its coverage: the share
    of its values found in the key, as real data hold rows whose reference is lost; none of
    unmistakable values, such as UUIDs, which are equal to those of another column by no chance. A
    column has one reference at most; where several keys may be the one, the profile holds each as a
    **reference candidate**, none of them preferred. Whether a row or many refer to one of the key,
    the keys of the table tell. A column of lists refers by the values of its lists, many to many: a
    row to as many of the key as its list holds values.
*   **Column group** - columns of a table filled together, such as the street, the postal code and
    the city of a delivery address: in mostly the same rows of its sample, a column filled in a row
    where it holds a value, neither null nor a sentinel. Found by the Jaccard index of the rows
    each two columns are filled in, it holds its columns and its coherence, and a column does not
    name its group. A column filled in nearly every row, or in too few of the sample to be judged,
    is in none.
*   **Column dependency** - columns of a table whose values follow from the value of another, its
    determinant, such as the name of a customer copied into each of its orders: each value of the
    determinant comes with one value of each dependent, in the rows the determinant is filled in.
    Columns that follow from each other, such as a code and its name, are equivalent determinants,
    held together. Found in the sample and verified on the whole table, it holds how strictly it
    holds, as real data hold exceptions. Where the determinant refers to a table, its dependents
    are copies of columns of that table, which a normalized model holds once. It tells which
    values follow from which, where a column group tells which columns are filled together.
*   **Entity** - the rows of a table of one entity of the business, where a table holds several:
    those of some values of its discriminator, each with the rows each column is filled in, so that
    the columns of its own are seen. Two values are of two entities where several columns are filled
    in nearly all the rows of the one and in nearly none of the other; counted on the whole table.
    An override gives entities by their values, and a harmonized name and a description of each,
    which the values found of none join.
*   **Discriminator** - the column whose values tell the entities of a table apart: an enumeration
    of no sensitivity, as in the single-table inheritance of a mapping of objects to tables, or a
    column of lists whose values are one, by them, a row counted with each value of its list. A
    table has one at most, and none where it holds the rows of one entity alone, unless an override
    gives it.
*   **Term** - a part of the original names, mostly an abbreviation: `CUST` in `CUST_CRT_DT`. The
    profile holds the terms of each name, as `describe` split it, each with the concepts written as
    it, its candidates, as the glossary had them then.
*   **Reading** - the concept each term of a name stands for, one word for each term at its place:
    `ap_ap_nm` read as AirPlus, contact person and name. `describe` reads a name whose terms have
    one candidate each, and keeps a reading while the terms of its name stay as they were split,
    their candidates among them; which concept a term of several stands for, the language model
    chooses, or an override gives. The terms and the reading of a name are written together, so that
    a profile never holds a reading of other terms than its own. A harmonized name is composed from
    the reading alone, unless an override gives the name.
*   **Vocabulary** - the terms a term written together is split into: those found in the names of
    a profile, and the terms its concepts are written as. A term is split only where other terms of
    the vocabulary cover it whole - `lfadr` in `KD_LFADR_PLZ` into `lf` and `adr` -, and a term a
    concept is written as never.
*   **Concept** - an entry of the glossary: a word, from which harmonized names are composed, the
    terms it is written as - its word, where the word is one term, and its abbreviations:
    `customer`, `cust` and `kd` for `customer` -, and its description, in English, from which the
    language model proposes descriptions of columns. A concept omitted is left out of the harmonized
    names, as a prefix that marks a custom column.
*   **Glossary** - the concepts of a profile, once for the whole profile, each under its word.
*   **Description** - what a column holds, in English, for a person who knows the business but not
    the database, proposed by the language model from the reading of its name, its statistics, its
    matches, its sample and its reference; its name is the harmonized one. What a table and the
    database hold are descriptions as well, given by hand alone, and shown to the language model
    with every question of them.
*   **Override** - what is given by hand of the profiles of a project, in its `overrides.yml` and
    the files of `overrides/`, or by a person answering `adopt`, and laid over a generated profile:
    what the database and a table hold, concepts of the glossary, the reading, the harmonized name
    and the description of a table or column, the sensitivity and the sentinels of a column, the
    primary key of a table, the reference of a column, or none, a column that determines no other,
    whatever is found, and the discriminator of a table, with the values, the name and the
    description of its entities, or none. What it gives is taken as given by the stage whose work it
    is, and counts once that stage runs again. A name given comes before the one composed from the
    reading, so that it resolves a collision of harmonized names, and a concept given before the one
    proposed of its word. Which stage takes what, when it counts, and what is refused,
    [PROJECT.md](PROJECT.md#the-overrides-overridesyml-and-overrides) says.
*   **Workspace** - the directory of samples and intermediate results; it may hold sensitive
    values, and keeps itself out of version control.

## How it works

1.  `scan` connects to the schema of an environment of a project as its user, the password taken
    from a variable, and selects the tables the project names, by a list or a regular expression.
    For each table it counts the statistics of all columns in one query, the approximate distinct
    counts included, the sentinels of each column counted apart and left aside; it counts the values
    of every column whose distinct count is at most the threshold of an enumeration; and it takes a
    sample into the workspace. The columns of lists are found in the sample, and the values of their
    lists counted, enumerated and matched as those of a column are. The detectors check the values
    of the sample, its sentinels aside; the semantic types they find are verified on the whole table
    by the patterns of the detectors in SQL. Its keys are indicated by the statistics and the
    sample, and verified on the whole table, and the primary key chosen among them, unless the
    overrides give it. The columns filled together in the sample are named as column groups, and the
    columns whose values follow from another in the sample, verified on the whole table, as column
    dependencies. Of the enumerations of no sensitivity - of the values of columns, and of those of
    the lists of a column of lists -, the one whose values tell entities of the rows apart is the
    discriminator, its entities counted by one more query, and one of each candidate of lists. The
    overrides of the project give the sentinels of a column in place of those of the tool, mark the
    columns the detectors miss, and give the primary key of a table, the columns that determine no
    other, its separator of lists, and its discriminator and entities of it, or none. The result is
    the profile, with the ranges and the values of enumerations of the columns of no sensitivity,
    written after every table: a scan that fails keeps the tables before it, and the next scan
    resumes its run, skipping the tables it counted, unless the overrides now give their columns,
    their primary keys or their discriminators otherwise, or their lists are of another separator.
    It updates the profile there is: the tables no longer selected are dropped, the others kept
    until they are counted anew, and what the other stages filled is kept - the glossary, the terms
    and readings of the names that stay, and the descriptions of the columns, but the references of
    a table counted anew and those to the tables dropped, until `relate` runs again; a profile
    scanned with other semantic types keeps its tables without their matches, values, ranges and
    discriminators, until they are counted anew. A profile that cannot be read, or one of another
    schema, is refused and never overwritten: it may be the work of hours.
2.  `relate` relates the tables of the profile to the keys of one column of each other, of another
    table or of the same, querying the database of the environment. It indicates the references by
    the profile alone: of columns whose type, distinct values, lengths, matches and range agree with
    a key, a run of whole numbers from the start of the key - short of its end, as a code or a
    counter is, or a key of its own table numbered from one - only where its name holds the terms of
    the key and of its table. It probes each by a hundred of its values, taken at random and looked
    up in the whole key by the database, so that no value leaves it, ten keys and fifty columns at
    most in a query, as each column costs a stage or two, of which a database allows only so many;
    UUIDs, unmistakable values, refer to a key where more than half of them are found, of several to
    the one of the most, and the coverage of others is counted on the whole table, a reference where
    nine of ten of its values are found. A column found in several keys has each as a reference
    candidate, ranked. The overrides give the reference of a column, or none: it is not searched,
    but measured, and warned of where its coverage, or the share probed of UUIDs, falls below what a
    reference is found at. A column of lists is indicated by the values of its lists - of digits, as
    numbers, where the key is of whole numbers -, and probed and counted on a source of a row of
    each of them, by queries of its own; it is not searched for a reference to a key of its own
    table, which that source would read so as well. The result is the profile, with the references
    and reference candidates of every table in place of those it had, written once at the end, so
    that a relate that fails leaves it as it was.
3.  `describe` splits the original names of all tables and columns into terms, those written
    together by the vocabulary, each with its candidates. It asks the language model of the project
    for the concept of each term of none, showing it the tables and columns the term appears in,
    with the values of their samples of no sensitivity, and proposes it into the glossary, a word
    there is taking the term as one more abbreviation. It splits the names again, reads each name
    whose terms have one candidate each, and asks the language model for the reading of each name of
    a term of several concepts, shown the concepts with their descriptions. From the reading of its
    name and the descriptions of its concepts, and from each column's statistics, matches, values,
    sample, the columns filled together with it and the key it refers to, with the reading of the
    name of that table, it asks for the column's description - its name stays the one harmonized; a
    reference candidate is not shown, as none of several keys is the one. Overrides are taken as
    given: no term of a concept given, no name of a reading given and no column of a description
    given is asked for. The language model is asked only for what the profile lacks, and the profile
    is written after each concept and each table read or described, so that a run interrupted is
    resumed; `describe --anew` drops first what the language model filled, and
    `describe --without-llm` asks it nothing, doing what needs no model alone: the names split, and
    read where each term has one candidate, the profile written once at the end. The result is the
    profile, with terms, glossary, readings and descriptions.
4.  `adopt` compares the concepts of the profile with those of the overrides, and asks a person at
    the terminal about what each adds: a description where none is given, and abbreviations no
    concept given has. Each answer is written at once, to the file of the overrides that gives the
    field, else to the first that names the concept, a new concept to `overrides/glossary.yml`,
    keeping the comments and the order of the file. The result is the overrides; it is the one stage
    that writes them, and it does so only as a person answers.
5.  `report` renders the profile, with the overrides laid over it, as HTML: what the database and
    each table hold, its keys, its references and reference candidates and the references to it,
    with a diagram of the tables connected to it, its column groups and column dependencies, the
    harmonized names and readings of the tables and columns, the descriptions of the columns, the
    entities of a table by the share of their rows each column is filled in, with the names and
    descriptions given of them, and the concepts proposed told apart from those given.

## Principles

The design repeats a few decisions; new code follows them.

*   **The profile holds no values of the columns found sensitive.** Raw values - the values of an
    enumeration, the range of a column - go into the profile only for columns of no sensitivity;
    samples stay in the workspace. A profile can be shared; a workspace cannot. Sensitivity is
    judged optimistically: a column is sensitive where a sensitive type is one of its matches, or of
    the matches of the values of its lists, or where an override marks it so - the mark comes first,
    and marks what the detectors miss -; each value that goes into the profile is checked on its own
    all the same, and withheld where it is of a sensitive type, a list where one of its values is.
    The sentinels of a column are no values of it, and go into the profile whatever its sensitivity:
    those of the tool are fixed texts, those given are of the overrides.
*   **No value leaves the machine.** The language model runs locally, and is reached past every
    proxy, as its prompts hold values of samples; no external service gets a value, a sample or a
    profile.
*   **The database is only read.** The tool sends nothing but queries; only the simulation
    writes, into its own environment.
*   **The dialect writes all SQL.** No other part of the tool writes SQL text, so that another
    database is a new dialect, not a change across the code. What the tables hold is counted or
    sampled by queries that the part that reads their rows builds from the building blocks of the
    dialect: metadata belongs to the source, counting and sampling to the parts that do them.
*   **Every attribute of the profile is filled by one step.** A step, `scan`, `relate` or a step of
    `describe`, replaces in a profile there is the attributes it fills alone, and keeps all others,
    so that a stage run again loses nothing another found: a scan keeps the terms and readings of
    the names and the descriptions of the columns, and splitting the names again keeps a reading
    while its terms stay. The references are the exception: they are of the values of two tables, so
    that a table a scan counts anew has none, until `relate` runs again. Which step fills which
    attribute is said once, in [PROFILE.md](PROFILE.md#which-stage-fills-what).
*   **Detectors decide, the language model names.** What a column is, is found by deterministic
    detectors that can be tested; the language model proposes the concepts of terms and the
    descriptions of columns from what they found, and nothing else. It is shown the values of a
    sample as far as the profile may hold them - none of the columns of a sensitivity, none of a
    sensitive type -, as what it answers goes into the profile; where it needs more, the overrides
    give it.
*   **One word per concept.** Harmonized names are composed from the words of the concepts of the
    glossary, through the reading of each name, so that the same concept reads the same in every
    table, under whichever of its terms it is written; a name of no reading has none. Where
    two columns of a table come to the same name, the report shows it, rather than one name taking
    the place of the other. An override gives a name in place of the composed one, which resolves a
    collision.
*   **The stages share nothing but the profile and the workspace**, besides the overrides, which a
    person keeps and `adopt` writes only as a person answers. Each stage can be run again on its
    own: `describe` with another model without querying the database, `report` without either.

## The repository

*   **`src/`** - the package `data_profiler`; **`tests/`** - its tests.
*   **`work/`** - scripts of trials, such as that of issue 04: not a part of the tool, run by hand,
    checked as its code is; what holds is built into the tool by an issue of its own.
*   **`examples/`** - example projects of the tool, such as `examples/crm/`, which profiles the
    simulation environment.
*   **`projects/`** - the projects profiled with the tool, in a repository of their own, cloned or
    made there apart from this one, which ignores it; it does not depend on this one, and lies here
    so that the dev container reaches it. That repository keeps its projects with the results of
    their environments, the work done; it ignores their `.env`, and their workspaces keep
    themselves out of version control.
*   **`simulation/`** - the project `simulation`, with its package in `simulation/src/`, its tests
    in `simulation/tests/`, an example profile in `simulation/profiles/`, and in
    `simulation/trino/` the configuration of the simulated Trino.
*   **`docker-compose.yml`** - the simulation environment, started as `README.md` says.
*   **`.devcontainer/`** - the dev container of Visual Studio Code, with Ollama beside it, for the
    machine that reaches the real database; the certificates of the company go into its `certs/`,
    which keeps them out of version control.
*   **`docs/`** - the documents of the project: this one, the
    [coding guidelines](CODING-GUIDELINES.md) and one document per subject that outgrew its section
    here (see the list below).
*   **`issues/`** - the issues, one file each, and the overviews generated from them, under areas
    that follow the parts above (see [issues/README.md](../issues/README.md)).
*   **`scripts/`** - the tools that check the rules of the documents, such as
    `scripts/wrapping.sh`, and that write their generated parts, `scripts/generate.py`.
*   **`.githooks/`** - the pre-commit hook, which runs the checks of the coding guidelines and keeps
    the issue overviews up to date; enabled per clone with `git config core.hooksPath .githooks`.
*   **`.claude/agents/`** - the agents Claude Code is given for the workflow of
    [AGENTS.md](../AGENTS.md#workflow), such as the `reviewer`.
*   **`AGENTS.md`** - how we work together; `CLAUDE.md` points Claude Code to it, and the links
    `.cursorrules` and `.clinerules` point Cursor and Cline to it.

## Documents

*   [CODING-GUIDELINES.md](CODING-GUIDELINES.md) - coding style, error handling, logging, tests,
    and the checks that run before every commit.
*   [PROJECT.md](PROJECT.md) - the configuration of a project and its overrides: what holds for
    them, recipes, and the reference of their fields.
*   [PROFILE.md](PROFILE.md) - the profile: its files, which stage fills what, what it never holds,
    and the reference of its fields.
