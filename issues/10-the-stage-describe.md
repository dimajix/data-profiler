# 10 — The stage describe

**Status:** open
**Type:** feature
**Priority:** high
**Area:** Describe
**Epic:** [02](02-first-version-epic.md)
**Summary:** Nobody proposes words for the terms or names and descriptions for the columns: the language model is not asked.

## The problem

The stage `describe` asks the local language model for the word of each term of the glossary
([09](09-the-glossary.md)), shown the columns it appears in, and then for the name and description
of each column, from its statistics, its matches, its sample and the glossary
(`docs/ARCHITECTURE.md`, "How it works"). None of it exists.

## Why it matters

It is what the tool is for: names a person with business knowledge reads without the original
abbreviations.

## What is to be decided

The answer of [04](04-can-a-small-model-name-columns.md) first: which model, and whether terms first
and columns second works. Then the interface, put before the maintainer.

- **Who owns the client of the language model.** An architecture question left open by
  [01](01-initial-project-setup.md): the database has a part and an interface of its own
  (`source`, `Source`, `SourceError`), the language model none. Either an interface of its own - a
  part `data_profiler.model` with an abstract class and an exception class, Ollama its first
  implementation -, or an internal of `describe`. The first lets `describe` be tested without
  Ollama; the second is one concept fewer while there is one model and one caller.
- **Structured answers.** Ollama's `format` with the JSON schema of the answer, so that an answer
  is parsed, not read.
- **Samples.** The language model may see the values of a sample (it runs locally); they come from
  the workspace, never into the profile or the log above `debug`.
- **Tests.** The prompts and the parsing without a model; one test against Ollama in the
  simulation environment, whose model has to be pulled once into its volume.

## Done when

- The interface is agreed with the maintainer.
- `data-profiler describe` writes a profile with the words of the glossary and a suggestion for
  every column - name and description -, against the simulation environment.
- `describe` can be run again with another model without querying the database.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-11-03** — The glossary becomes one of concepts ([27](27-glossary-of-concepts.md)):
  `describe` proposes for each term of no concept a new concept, of its word and description, or
  the term as an abbreviation of a concept there is, and may propose another concept of a term
  where none fits the columns it appears in; for a column, it chooses the meaning of each term of
  several concepts, and proposes its name and description from the concepts of its terms. Whether
  the words of concepts whose terms no name has any longer are dropped is decided here.

- **2026-11-03** — The terms and readings of the names are steps of `describe` of their own
  ([28](28-terms-and-readings.md)): this issue adds the steps of the language model - concepts of
  the terms of none, the reading of a name of a term of several concepts, in the step that reads
  the names, and the names and descriptions -, and the override of the name of a column, which
  resolves a collision of harmonized names.
