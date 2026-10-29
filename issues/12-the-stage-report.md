# 12 — The stage report

**Status:** open
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
