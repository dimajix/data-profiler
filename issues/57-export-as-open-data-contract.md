# 57 — Export as Open Data Contract

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Export
**Summary:** The profile can only be exported as an HTML report, a document for people, so that what the tool found - the tables, columns, keys, references, sensitivity, descriptions - cannot be handed to the catalogs and tools that read an Open Data Contract Standard (ODCS) contract.

## The problem

The stage `report` renders the profile, with the overrides laid over it, into one HTML document.
The maintainer wants the same result as structured data as well, in the format of the Open Data
Contract Standard (ODCS, Bitol, Linux Foundation; version 3.2.0 at the time of writing), which data
catalogs, quality tools and the `datacontract` CLI read.

The idea of the maintainer: the stage `report` becomes `export`, and takes a **template** - `html`
as now, and new `odcs`. Each template lies in a directory of its name, and may consist of several
files.

## What ODCS asks for

Read from the standard's documents (`docs/fundamentals.md`, `schema.md`, `references.md`,
`data-quality.md`, `infrastructure-servers.md` in `bitol-io/open-data-contract-standard`):

**Required by the standard.** At the top: `apiVersion`, `kind` (always `DataContract`), `id`,
`version` and `schema`; per element of the schema - a table or a column - its `name`. Everything
else is optional, among it `name`, `status`, `domain`, `tenant`, `description`, `servers`, `team`,
`tags`, `customProperties`. A server of type `trino` requires `catalog`, `host`, `port`, `schema`.

**What the profile gives at once** (a mapping to be settled in the work, not decided here):

| ODCS | From the profile |
|---|---|
| `apiVersion`, `kind` | fixed by the tool |
| `servers[]` (`type: trino`, `catalog`, `schema`, `host`, `port`) | the environment: its URL |
| `description.purpose` | the description of the database, given by hand |
| schema object `name` / `physicalName` / `physicalType: table` | harmonized name / original name / `table` |
| object `description`, `businessName`, `synonyms` | description of the table; harmonized name; original name |
| property `name` / `physicalName` | harmonized name / original name of the column |
| `logicalType`, `physicalType` | the type of the column, mapped (`bigint` to `integer`, `varchar(n)` to `string`, `decimal` to `number`, ...), as the database names it |
| property `description` | description of the column |
| `primaryKey`, `primaryKeyPosition` | the primary key of the table |
| `unique` | a key of one column |
| `relationships` (`type: foreignKey`, `to`) | the references of a column - not the reference candidates, none of which is preferred |
| `classification` | the sensitivity of the column (`personal`, `payment-card`) |
| `tags` | the semantic types found in the column |
| `logicalTypeOptions` (`maxLength`, `minLength`, `format: uuid`, `minimum`, `maximum`) | lengths, range, the match of the type uuid |
| `examples` | the values of an enumeration, of no sensitivity |
| `quality` (library metrics `rowCount`, `nullValues`, `missingValues`, `invalidValues`, `duplicateValues`) | rows, nulls, sentinels, matches, distinct counts |
| `customProperties` | what ODCS has no field for: column groups, column dependencies, entities, coverage of references, the glossary |

**What it cannot give**, because nothing in the database says it: `id`, `version`, `status`,
`domain`, `tenant`, `team` and owner, the SLAs, roles and support channels, the price. Of these, the
standard requires `id` and `version`.

## Considerations

**Is an ODCS export one file?** Not necessarily, but the standard has no way to split *one*
contract.

- A contract is one YAML file, and its `schema` is an array, so one file may hold any number of
  tables; the tools read it so (DataHub makes a dataset of each entry).
- Several contracts - one per table - are allowed: each is a complete contract of its own, with its
  own `id`, `version` and `apiVersion`. Since ODCS 3.1 a foreign key may point into another
  contract by a reference, `customers.odcs.yaml#/schema/customers_tbl/properties/cust_id_pk` in
  `relationships[].to`; the standard says that references are, for now, only supported for foreign
  keys. Nothing else - a description, a quality rule - may be written outside the file.
- A split by file is therefore a split of contracts, not of one contract, and each file needs the
  fields only a person can give. One file per schema keeps the references inside it, in the short
  notation (`ord.cust_id` to `cust.cust_id`), and one `id` and one `version` for what is one
  schema. **Recommendation: one file per environment** - the profile is one schema, and a catalog
  imports a contract as a unit - and one contract per table only if a user asks for it.

**What the project has to give - new fields of `project.yml`, optional until ODCS is exported**
(proposal): `id` of the contract - a stable one, as a UUID or a name, which the tool must not
make up anew with every export - and its `version`, with `status`, `domain`, `tenant`, `name`, and
`description.purpose`, `usage`, `limitations` as the overrides give the description of the
database today. Open: per project or per environment (`dev` and `prod` are one contract with two
`servers`, or two contracts?), and whether `version` is kept by hand or raised by the tool when the
schema it exports changes (a changed column is a breaking change of a contract).

**A profile says what is, a contract says what shall hold.** The tool finds that a column has no
nulls, that its longest value has 22 characters, that it matches an IBAN in all rows. A contract
states this as a promise to its consumers. Exporting all of it as rules would turn what was
observed into what is demanded, and the next load fails the contract. Options: export the
observations as `customProperties` and `description` only, rules only where a person confirmed them
in the overrides, or rules with the observed value and a switch. To be decided by the maintainer; it
changes which of the table's rows go into `quality`, `required`, `unique` and `logicalTypeOptions`.

**No value without disclosure.** `examples` and `enum` carry values: they go in by the rule of
`disclosure` alone - a column of a sensitivity or a sensitive type shows none - and the same holds
for `minimum`/`maximum`. The exporter does not read the workspace.

**What a template is.** Today `report` is a Jinja2 template, `templates/report.html` with
`report.css`, and the code that feeds it (`data_profiler.report`, `diagram`). YAML written by a
text template is fragile - quoting, indentation, escaping of descriptions in several lines - and
the contract has to be valid against the JSON schema of the standard. Options:

1.  **A template is a directory the exporter renders** - for `odcs` too, as Jinja2 files. One
    mechanism, several files per template as the maintainer wants; the YAML is built by text.
2.  **A template is an exporter of its name**, a type with `export(profile, overrides, directory)`,
    whose files, if it uses templates, lie in `templates/<name>/`; `odcs` builds a dictionary and
    dumps it with the YAML library the tool already uses for its documents, `html` renders its
    Jinja2 template. The directory of a template holds what the exporter needs, nothing fixed.
3.  As 1, but `odcs` is a template that fills a dictionary through a Jinja2 macro set - no gain
    over 2.

Recommendation: 2. It follows how the tool writes YAML already (`documents`, `files`), and the
checks - the schema of the standard, a round trip - run on the dictionary.

**Where the result goes.** Today `<environment>/report.html`. A template may write several files,
so a directory: `<environment>/export/<template>/` (`index.html`, `contract.odcs.yaml`), and the
command's argument is the template: `data-profiler export simulation --template odcs`. Whether
`--template` defaults to `html` or is required is open; the rename breaks every script that calls
`report` - the old name need not stay, the project is at its beginning.

**The name of the stage and its concepts.** `export` is a stage as `report` is: it reads the
profile and the overrides, nothing else. The docs say "report" in ARCHITECTURE.md (Parts, Stage, How
it works), PROJECT.md (directory of an environment, "taken by `report`" in the table of the
overrides), the module `data_profiler.report`, `Environment.report`, the issue area `Report` in
`issues/generate.sh` and `issues/README.md`, and the code of the report that the template `html`
keeps: the word *report* stays for the HTML document, the stage is renamed.

**Steps** (restructure, then extend, each reviewed and committed apart):

1.  Rename the stage `report` to `export` with the one template `html`, its place in the directory
    of the environment, the documents, the area - no change of what is written.
2.  Introduce the template as a concept: the exporters by name, the argument of the command.
3.  The fields of the contract in `project.yml` (and `docs/PROJECT.md`), with their format version.
4.  The template `odcs`: the mapping above, tested against the JSON schema of the standard (to be
    checked: it is published in the repository of the standard; a test dependency, or a copy
    pinned in `tests/`).
5.  Optional fields filled from the profile, as far as the decision on observed rules allows.

## Questions for the maintainer

1.  One file per environment, or one contract per table too?
2.  `id`, `version`, `status`, `domain`, `tenant` in `project.yml` - per project or per
    environment? `version` by hand, or raised by the tool?
3.  Observations as `customProperties` alone, rules only where confirmed in the overrides, or
    rules with the observed values?
4.  A template as an exporter (option 2), or a rendered directory (option 1)?
5.  Output in `<environment>/export/<template>/`, `--template` required or defaulting to `html`?
6.  Which optional parts of ODCS are of interest beyond the above? `team`, `roles` and
    `slaProperties` cannot be found by the tool, and would come from the project too.

## Done when

`data-profiler export <environment> --template odcs` writes a contract that validates against the
JSON schema of the ODCS version the tool names, with every field the standard requires, taken from
the project or the profile, and every optional field the profile and the project can fill; the
template `html` writes the report as before; `report` is gone from the command line, the code and
the documents; the documents say what the project gives for the contract.

## History

2026-11-12: Opened on the maintainer's request. Researched the standard (v3.2.0): required fields,
splitting of contracts, relationships and quality library; nothing built yet.

2026-11-12: The maintainer decided three of the questions. Question 3: the contract exported is a
basis, an inventory of what was observed, which the experts then extend and rework into what is
binding; so the observations are exported as rules, with the values observed - `required`,
`unique`, `logicalTypeOptions` and `quality` filled from the profile. Question 4: a template is an
exporter of its name (option 2), its files, where it has any, in `templates/<name>/`. Question 5:
the result goes to `<environment>/export/<template>/`, the template is chosen by `--template`, and
the command `report` is gone; whether `--template` defaults to `html` is still open. Questions 1,
2 and 6 are still open.

2026-11-12: The maintainer decided the rest. Question 1: one file per environment. Question 2: the
fields of the contract are given per project, in `project.yml`; `version` is kept by hand, for now.
Question 5: `--template` defaults to `html`. Question 6: no optional parts beyond those the profile
fills - no `team`, `roles` or `slaProperties`. The status of a contract exported is `draft`. The
rules are qualitative alone, none quantitative: as the number of rows and of values changes from
one load to the next, no rule counts - no `rowCount`, no share of nulls, no coverage -, but a rule
says what holds of every row: a column with no nulls, with no sentinels, unique, of the values of
its enumeration. Proposed for the agreement, from the profile:

- `required: true` where a column has no nulls; a `missingValues` rule of its sentinels -
  those of the tool or those given - `mustBe: 0` where it has none of them either.
- `unique: true` for a key of one column; a `duplicateValues` rule of the schema over its columns,
  `mustBe: 0`, for a key of two.
- `enum` of the values of an enumeration of no sensitivity.
- A semantic type every value of the whole table matches - its share of the table 1 - as a tag,
  and `logicalTypeOptions.pattern` of its detector; `format: uuid` for the type uuid. A type of a
  smaller share is a tag alone.
- `minLength` and `maxLength` only where all values are of one length, as a code is; no range and
  no other lengths, which every load may extend.
- The references as relationships, without their coverage; no reference candidates.
- Column groups, column dependencies and entities left out, as nothing reads them from a contract
  yet and the report shows them.

2026-11-12: The maintainer decided, against the proposal above, that the lengths and the range go
into the contract as well, as rules the experts judge and adjust: `minLength` and `maxLength` of
every column of text, from its shortest and longest value, and `minimum` and `maximum` - the names
ODCS gives them in `logicalTypeOptions`, of numbers as of dates and times - from its range. The
profile holds both already, `statistics.lengths` and `statistics.range`, so that the scan needs no
change. A range withheld - of a column of a sensitivity, or a value of a sensitive type - gives no
`minimum` and `maximum`, as `disclosure` decides for the profile.

2026-11-12: Step 1 agreed and done. The stage `report` is the stage `export`; it writes the report
as `export/html/report.html` in the directory of the environment, `Environment.export(template)`
naming the directory of a template, and `write_report` makes the directory it is given. The files
of the template `html` moved to `templates/export/html/`, apart from the prompts of `describe` in
`templates/prompts/`. The word *report* stays for the HTML document - the module
`data_profiler.report`, `write_report`, `ReportError` -, so that "`report` is gone" in *Done when*
means the stage: the command line, and the documents where they name the stage. The area `Report`
of the issues is `Export`, in the field lines of the issues of it as well; their descriptions stay
as they are.

2026-11-12: Step 2 agreed and done. The module `data_profiler.export` holds the `Template`, a form
the profile is exported in, by its name, with `write(profile, overrides, directory)`, and its
`ExportError`, as `llm` holds the `LanguageModel` and its error; the concept has one name, the
template, in the code as in the documents and the option, rather than an exporter beside it. The
report is the template `Report`, of the name `html`: its class names what it writes, its name the
format. `write_report` and `ReportError` are gone. The command line holds the templates by their
names, as it makes the language model - `export` cannot, as `report` imports it -, and takes
`--template`, of the report where none is given.

2026-11-12: After the review of step 2, the maintainer decided three findings. `Environment.export`
takes the name of a template, `name`, as `Project.environment` takes that of an environment, since
a template in the code is a `Template` now; changed with step 2. Before the template `odcs`, a step
of its own moves what every template would repeat into `Template.write`: laying the overrides over
the profile, making the directory, writing each file whole and translating an `OSError` into an
`ExportError`; a template gives its files alone, by an abstract method that takes the profile with
the overrides laid over it, and the overrides. And the word *template* keeps one meaning: the Jinja2
files of the prompts of `describe` and of the report, the comments that call them templates, and
the package directory `templates/` are named otherwise, in this issue, by a step of its own.

2026-11-12: The step of the findings above that renames the Jinja2 files agreed and done: the word
*template* keeps the meaning of the stage `export`, and *prompt* that of the text the language
model is asked. The Jinja2 files are called so, and the package directory `templates/` is `jinja/`,
with the files of the prompts of `describe` in `jinja/prompts/` and those of the template `html` in
`jinja/export/html/`, not in `templates/html/` as the considerations above say; a template that
renders no Jinja2 file, as `odcs` is to build a dictionary, has none. The step of `Template.write`
follows, then the fields of the contract and the template `odcs`.

2026-11-12: The step of `Template.write` agreed and done. `Template.write` is concrete: it warns of
what the overrides give that the profile does not take, lays them over it, makes the directory and
writes each file whole, translating an `OSError` into an `ExportError`. A template gives its files
alone, by the abstract `Template.files(profile, overrides)`, public, so that its content is tested
without the file system: of the profile with the overrides laid over it, and the overrides, the
content of each file by its name in the directory. `Report.files` gives `report.html`, rendered by
the function of the module, now private, which lays nothing over. The fields of the contract and
the template `odcs` follow.
