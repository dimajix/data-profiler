# 32 — A description of the database

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Describe
**Summary:** Nothing tells the language model what the database is about - the business it serves, what its tables hold -, so that it proposes concepts, chooses readings and describes columns from the names, values and statistics of one column alone, without the context a person who knows the business has.

## The problem

The prompts of `describe` show the language model a term with the names it appears in, a name with
the candidates of its terms, or a column with its facts. Nothing says what the database as a whole
is: the CRM of a wholesaler, the bookings of an airline. A term such as `ap` or `seg` means one
thing in one business and another in the next, and the model has to guess the business from the
names.

## Why it matters

A small local model is the more dependent on context the less it knows by itself
([04](04-can-a-small-model-name-columns.md)). A sentence or two of what the database is about is
little to write, the same for every prompt, and is what a person would be told first.

## What is decided

As discussed with the maintainer:

- **Where it is given:** in `overrides.yml`, beside the glossary, as what is given by hand of the
  profiles of a project, the same for all its environments - not in `project.yml`, which configures
  how the tool works, not what the data mean.

  ```yaml
  description: >-
    The CRM of a wholesaler of office supplies: its customers, mostly companies, their contacts and
    addresses, and their orders.
  ```

- **How it reaches the model:** through the overrides, which `describe` holds already; no new
  parameter, and not through a context of the language model, which holds services, not what is
  given by hand.

## What is to be decided

- **The prompts:** which of the three show it - the concept, the reading, the description of a
  column -, and where in them.
- **The report:** whether it shows the description, above the tables.
- **The format:** the overrides are raised to the next version.
- **Later, not in this issue:** a description given of a table, `tables: cust: description: ...`,
  in the same way; and one proposed by the language model, which the one given comes before, as for
  the columns.

## Done when

- The overrides give a description of the database, and the prompts of `describe` show it.
- The example gives one.

## History

- **2026-11-04** — Opened from the discussion of [31](31-describe-without-llm.md): a description of
  the database is to give the language model the context of the business.
