# 32 — Descriptions of the database and its tables

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Describe
**Summary:** Nothing tells the language model what the database is about - the business it serves - or what a table holds, so that it proposes concepts, chooses readings and describes columns from the names, values and statistics of one column alone, without the context a person who knows the business has.

## The problem

The prompts of `describe` show the language model a term with the names it appears in, a name with
the candidates of its terms, or a column with its facts. Nothing says what the database as a whole
is: the CRM of a wholesaler, the bookings of an airline; nor what one of its tables holds: the
customers, the positions of an order. A term such as `ap` or `seg` means one thing in one business
and another in the next, and the model has to guess the business from the names, and what a table
holds from the names of its columns.

## Why it matters

A small local model is the more dependent on context the less it knows by itself
([04](04-can-a-small-model-name-columns.md)). A sentence or two of what the database is about is
little to write, the same for every prompt, and is what a person would be told first; a sentence of
what a table holds is the same for every column of it.

## What is decided

As discussed with the maintainer:

- **Where they are given:** in `overrides.yml`, as what is given by hand of the profiles of a
  project, the same for all its environments - not in `project.yml`, which configures how the tool
  works, not what the data mean: the description of the database beside the glossary, and the
  description of a table beside its columns, as the description of a column is given.

  ```yaml
  description: >-
    The CRM of a wholesaler of office supplies: its customers, mostly companies, their contacts and
    addresses, and their orders.
  tables:
    ord_itm:
      description: The positions of an order, one product each, with its quantity and price.
      columns:
        ...
  ```

- **How they reach the model:** through the overrides, which `describe` holds already; no new
  parameter, and not through a context of the language model, which holds services, not what is
  given by hand.

- **Two steps.** First, without a change of behaviour, the prompts are rendered by templates, as
  the report is: today they are put together in the code, of strings joined, lines appended and a
  template filled at the end. Each prompt becomes one Jinja2 template, holding as much of it as it
  can - its text, its conditions and its loops -, and the code gives it the objects it shows, and
  the values of a sample as the module `disclosure` lets them be shown, never the sample itself.
  Then the descriptions, which go into the templates.

## What is to be decided

- **The templates:** where they are - beside the report in `templates/`, or in a directory of
  their own -, and their environment: no escaping, as a prompt is no HTML, and undefined names
  refused, as for the report.
- **The prompts:** which of the three show them - the concept, the reading, the description of a
  column -, and where in them: the description of the database in every prompt; that of a table
  where the prompt is of the table or of a column of it, and, for a concept, of the tables its term
  appears in.
- **The report:** whether it shows them, that of the database above the tables, that of a table
  under its name.
- **The profile:** whether the description of a table is held by `Table`, laid over by the
  overrides as the description of a column is, or by the overrides alone.
- **The format:** the overrides are raised to the next version.
- **Later, not in this issue:** descriptions of the database and of a table proposed by the language
  model, which those given come before, as for the columns.

## Done when

- The overrides give a description of the database and of each table, and the prompts of `describe`
  show them.
- The example gives a description of the database and of a table.

## History

- **2026-11-04** — Opened from the discussion of [31](31-describe-without-llm.md): a description of
  the database is to give the language model the context of the business.

- **2026-11-04** — The maintainer took the descriptions given of the tables into this issue, which
  were to come later.

- **2026-11-04** — The maintainer asked that the prompts be rendered by templates, holding as much
  of them as they can, conditions and loops among them; it is the first step of this issue.
