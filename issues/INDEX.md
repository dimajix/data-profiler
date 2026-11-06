# Issues — Index

Every issue, one line each, under its area and by number. Generated from the field lines of the
issue files by `issues/generate.sh` - never edit it by hand: change the issue file, and the
pre-commit hook (`.githooks/pre-commit`) or a run of the script brings this file up to date. How
issues are kept is described in [README.md](README.md); those open or in progress are listed in
[OPEN.md](OPEN.md).

## Profile

| No. | Status | Issue |
|---|---|---|
| [03](03-the-profile.md) | done | There is no profile yet: the stages have no format in which to hand on what they found about a database. |
| [11](11-overrides.md) | done | A wrong proposal cannot be corrected for good: a correction made in the profile is lost at the next run of describe. |
| [19](19-names-of-tables-that-differ-in-case-alone.md) | open | Two tables whose names differ in case alone, `Cust` and `cust`, get two files of the profile and of the workspace that are one file on a file system that ignores case, as those of Windows and macOS do. |
| [26](26-overrides-read-by-scan.md) | done | A profile written by scan holds the range and the values of the columns an override marks sensitive, as scan does not read the overrides, so that the profile, which is shared, holds what the overrides were to withhold. |
| [30](30-abbreviations-given-that-no-name-has.md) | done | An abbreviation the overrides give that no name of the profile has ends `describe` and `report` with an error, though the overrides are the same for all environments of a project and its glossary may well hold terms of tables that one environment does not have, or not yet. |

## Scan

| No. | Status | Issue |
|---|---|---|
| [06](06-source-and-dialect-for-trino.md) | done | The tool cannot reach a database: nothing connects to Trino, lists its tables or sends it a query. |
| [07](07-the-stage-scan.md) | done | Nothing counts what the columns of a table hold - their nulls, their distinct values, their ranges, whether they are enumerations - and nothing takes a sample of them. |
| [18](18-a-scan-written-table-by-table.md) | done | A scan writes its profile only once it has counted every table, so that a run that fails or is interrupted at one table loses all the tables before it, and a new scan replaces the profile whole. |
| [23](23-sentinel-values.md) | done | A value that stands for no value - an empty text, `00000`, `9999-12-31` - is counted as a value like any other, so that a column of them looks filled, its range runs to the sentinel, and its share of a semantic type falls below the threshold. |
| [25](25-groups-of-columns-filled-together.md) | done | Nothing tells which columns of a table are filled together - the street, postal code and city of a different delivery address -, so that columns that belong together are named and described each on its own. |
| [34](34-primary-keys.md) | done | Nothing tells which columns identify the rows of a table, so that a data model derived from the profile has no keys, and no reference of another table can be found to them. |
| [36](36-entities-of-a-table.md) | done | A table that holds the rows of several entities of the business - told apart by a simple condition, such as the value of a column of their kind, each with columns of its own filled - is profiled as one, so that nothing tells which entities it holds and which columns belong to each. |
| [37](37-values-determined-by-another-column.md) | open | Nothing tells which columns of a table are determined by another column than its key - the name of a customer repeated in each of its orders -, so that values copied from another entity, which a normalized model holds once, are not seen. |

## Relate

| No. | Status | Issue |
|---|---|---|
| [35](35-references-between-tables.md) | in progress | Nothing tells which columns of a table refer to the key of another - the customer of an order -, so that the relationships between the tables, which a data model is made of, are left to a person to find. |

## Detection

| No. | Status | Issue |
|---|---|---|
| [08](08-detection.md) | done | Nothing recognises what the values of a column are - phone numbers, postal codes, IBANs, card numbers, dates -, nor whether they are sensitive. |
| [15](15-a-detector-of-uuids.md) | done | Nothing recognises a column of UUIDs written as text, so that a key of that kind is told to the language model as nothing but a text. |
| [16](16-semantic-types-of-a-project.md) | done | The semantic types are fixed in the code, so that a pattern of one database alone - an account number `A` and ten digits - cannot be recognised without changing the tool. |
| [20](20-detectors-of-boolean-pairs.md) | done | Nothing recognises a column of flags written as `true`/`false`, `yes`/`no` or `0`/`1`, so that a flag is told to the language model as nothing but a text or a number. |
| [21](21-a-detector-of-free-text.md) | done | Nothing recognises a column of free text - comments, notes, descriptions -, so that it is told to the language model as a text like any other, and its values are disclosed like those of a code. |
| [22](22-a-condition-of-a-column.md) | done | A detector judges each value on its own, against one threshold of all types, so that a type that shows only in the values of a column together - a pair of flags, free text - cannot be recognised. |

## Describe

| No. | Status | Issue |
|---|---|---|
| [04](04-can-a-small-model-name-columns.md) | in progress | Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it. |
| [09](09-the-glossary.md) | done | The original names are not split into their terms, so nothing can give a term one word for the whole database and compose harmonized names from it. |
| [10](10-the-stage-describe.md) | done | Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked. |
| [24](24-terms-written-together.md) | done | Terms written together without a separator, `LFADR` in `KD_LFADR_PLZ`, stay one term, so that the glossary needs a word for every combination of terms, and the same term reads differently where it is written together. |
| [27](27-glossary-of-concepts.md) | done | The glossary gives each term one word and nothing else, so that two abbreviations of one concept are two entries, an abbreviation of several meanings has one of them, a prefix that means nothing becomes part of every name, and the language model is told no more of a term than a word. |
| [28](28-terms-and-readings.md) | done | The terms of a name are computed whenever they are needed, and which concept a term of several stands for is said nowhere, so that the split of a name changes unseen with the profile, a name of a term repeated in two meanings cannot be read, and a scan would lose what was found of the names. |
| [29](29-the-word-of-a-concept-as-a-term.md) | done | A concept is written only as its abbreviations, not as its word, so that a name written in full - `name`, `customer_id` - finds no concept until its word is given once more as an abbreviation, and a concept cannot be given without abbreviations at all. |
| [31](31-describe-without-llm.md) | done | `describe` cannot run without the language model of its project, though splitting the names and reading those of one candidate for each term needs none, so that a person working on the glossary waits for Ollama at every run, and cannot run it at all where Ollama is not there. |
| [32](32-descriptions-of-the-database-and-its-tables.md) | done | Nothing tells the language model what the database is about - the business it serves - or what a table holds, so that it proposes concepts, chooses readings and describes columns from the names, values and statistics of one column alone, without the context a person who knows the business has. |

## Report

| No. | Status | Issue |
|---|---|---|
| [12](12-the-stage-report.md) | done | What the tool found can only be read as YAML: there is no report a person reads. |

## Command line

| No. | Status | Issue |
|---|---|---|
| [13](13-projects-and-environments.md) | done | Nothing keeps the configuration of a database together with the results of profiling it, so every run is given the URL, the tables and the paths anew, and the same database in dev, test and prod cannot be profiled side by side. |
| [17](17-the-user-apart-from-the-url.md) | done | The user of an environment is part of its URL, so that it cannot be taken from a variable while the host, the catalog and the schema stay in the configuration the team shares. |

## Simulation

| No. | Status | Issue |
|---|---|---|
| [05](05-the-simulation-environment.md) | done | There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed. |

## Architecture

| No. | Status | Issue |
|---|---|---|
| [02](02-first-version-epic.md) | open | The tool does not exist yet: nothing scans a database, proposes names for its columns or reports what was found. |
| [33](33-major-and-minor-versions-of-the-formats.md) | done | The version of a format is raised with every change to its fields, and a document of another version is refused, so that a field added as optional makes every profile be scanned again and every `overrides.yml` and `project.yml` be edited by hand, though the document the version before wrote is read as it was. |
| [38](38-a-data-model-derived-from-the-profile-epic.md) | open | The profile describes the tables as they are, but nothing derives from it a data model that fits the processes of the business: the tables renamed, split into the entities they hold, with their keys and the references between them. |

## Tooling and process

| No. | Status | Issue |
|---|---|---|
| [01](01-initial-project-setup.md) | done | The repository is still the generic project template: its documents, checks and issue areas say nothing yet about this project, its language or its tools. |
| [14](14-a-dev-container.md) | in progress | The tool cannot be run on the machine that reaches the real database in a prepared environment: it has to be set up there by hand, on Windows, with its proxy, its certificates and a local language model. |
