# 10 — The stage describe

**Status:** in progress
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

## How

As agreed with the maintainer, in three steps, each a commit of its own:

- **The part `data_profiler.model`** - `Model`, a language model that answers a prompt in the form
  of a JSON schema, `ModelError`, and `Ollama`, its first implementation, without thinking, at
  temperature 0. Ollama is reached past every proxy: the prompts hold values of samples, which a
  proxy would take off the machine. `describe` parses each answer by the form it asked for; an
  answer not of it is skipped with a warning, a model that cannot be reached ends the stage.
- **The configuration.** `project.yml` names the model of the project, `model`, so that its
  results rest on one; where Ollama answers is a matter of the machine, the variable
  `OLLAMA_HOST`, else `http://localhost:11434`. The first model is `qwen3.5:2b`, the better one of
  the trial of [04](04-can-a-small-model-name-columns.md), which stays open for the run on the real
  database.
- **Asked once.** `describe` asks only for what is missing - the concept of a term of none, the
  reading of a name of a term of several concepts, the description of a column of none -, and
  writes the profile after each concept and each table, so that a run interrupted is resumed by
  the next. `describe --anew` drops first what the language model filled, to describe again with
  another model.
- **A reading is kept** while the terms of its name stay as they were split, their candidates
  among them; a term that gains a concept has its name read anew, by the language model where it
  has several. This settles the question [28](28-terms-and-readings.md) left: a reading derived
  from one candidate no longer survives a second.
- **Concepts proposed.** For each term of no concept, the language model proposes a word and a
  description, shown the names it appears in. A word the glossary has takes the term as one more
  abbreviation, so that a term proposed as an abbreviation of a concept there is needs no case of
  its own. The proposals go into the glossary of the profile; the glossary of the overrides is
  kept by hand, and the report tells both apart. An abbreviation of a concept proposed that no name
  has any longer is dropped, and a concept left without any. A concept of another meaning, where
  none fits a term, is not proposed: an override gives it.
- **Descriptions, not names.** The language model proposes the description of a column alone; its
  name stays the harmonized one, composed from its reading, so that one word stays one concept.
  Should the names not satisfy, the maintainer opens an issue of its own. The overrides give the
  name and the description of a table or column, the name to resolve a collision of harmonized
  names.

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

- **2026-11-03** — Planned with the maintainer (see How): a part of its own for the language model,
  concepts proposed into the glossary of the profile, readings chosen among the candidates, and
  descriptions of columns, their names composed from their readings.

- **2026-11-03** — Step 1 made: the part `data_profiler.model`, the model of a project, and the
  concepts proposed of the terms of none, against the simulation environment with `qwen3.5:2b` in
  about 30 seconds for 52 terms. The prompt does not show the words of the glossary: shown them,
  the model took one of them for nearly every term after, `customer_code` for `qty` and `iban`.
  Without them, its words are about as good as in the trial of
  [04](04-can-a-small-model-name-columns.md), its descriptions mostly of the abbreviation rather
  than of the concept. A concept given now keeps the abbreviations proposed of its word, so that a
  term the model reads as a concept given is of it.

- **2026-11-03** — Before step 2, as the maintainer decided: how the tool takes a value of the
  database - a count as a number, any value as text - moved from `data_profiler.source` to a part
  of its own, `data_profiler.values`, so that `describe`, which reads no database, no longer
  depends on the part that does.
