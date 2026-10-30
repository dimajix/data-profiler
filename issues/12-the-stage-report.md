# 12 — The stage report

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Report
**Epic:** [02](02-first-version-epic.md)
**Summary:** What the tool found can only be read as YAML: there is no report a person reads.

## The problem

The stage `report` renders the profile, with the overrides laid over it, as HTML
(`docs/ARCHITECTURE.md`, "How it works"). It does not exist.

## Why it matters

The report is what reaches the people with business knowledge, for whom the data model is made; a
profile is for the tool and for whoever corrects it.

## What is to be decided

- **One file.** A single HTML file with its styles inside, so that it can be sent on its own;
  Jinja2 for the template.
- **What it shows.** Per table its columns: original name, harmonized name, description, type,
  semantic type, statistics; the glossary of the whole database. Which of these first is put
  before the maintainer as a sketch.
- **Style sheets in the repository.** With the first file of CSS, `css` is added to the list
  `block` of `scripts/wrapping.sh`, which waits for it.
- **PDF.** Not in the first version; the HTML is made so that it prints, and a PDF can follow from
  it.

## Done when

- `data-profiler report` writes an HTML report of a profile, overrides laid over it, which a
  browser shows without anything else.
- `README.md` says how a report is made.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-30** — Done, after the sketch and the interface were agreed with the maintainer: the
  module `data_profiler.report` renders a profile as one HTML document, from a Jinja2 template
  that escapes what it shows, with its styles inside and no script; each table with its
  harmonized name and its rows, each column with its original and harmonized names, type, nulls,
  distinct values, lengths, range, semantic types with their shares and its sensitivity, found or
  marked, the values of an enumeration below it; and the glossary, each term with its word and
  where it appears. The command `data-profiler report ENVIRONMENT [--project DIR]` lays the
  overrides of the project over the profile of the environment and writes `report.html` beside
  it, whole or not at all. `css` is checked by `scripts/wrapping.sh`. Two details differ from the
  interface agreed, for the maintainer's review: beside `render`, a function `write_report` with an
  exception class of its own, `ReportError`, as a file that cannot be written has to be told by
  the class of the stage; and the name of the environment is not in the report, which `render`,
  given the profile alone, does not know. Descriptions of the columns come with
  [10](10-the-stage-describe.md).
  After the review: the style sheet is included by the template, not escaped as a value; an end of
  a range is said to be withheld only where it is None, so that an empty text is shown as one; a
  mark of no sensitivity is shown beside the matches it overrules; the template is laid out within
  100 characters.
  As the maintainer decided then: an environment of a project resolves its URL and password when
  they are asked for, so that `report`, which does not reach the database, needs neither its
  password nor the variable of it; and a column tells by `Column.sensitive` whether it is of a
  sensitivity, which `disclosure`, `report` and its template asked each in a way of their own.
