# 31 — describe without a language model

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Describe
**Summary:** `describe` cannot run without the language model of its project, though splitting the names and reading those of one candidate for each term needs none, so that a person working on the glossary waits for Ollama at every run, and cannot run it at all where Ollama is not there.

## The problem

`describe` makes the language model of the project, and fails where `project.yml` names none or
Ollama cannot be reached. Of its steps, only some ask the model: proposing a concept of a term of
none, choosing the concept of a term of several in a name, and describing a column. Splitting the
names into their terms, dropping the abbreviations no name has, and reading a name whose terms have
one candidate each need none.

## Why it matters

A glossary is built in rounds: give concepts in `overrides.yml`, describe, look at the terms of no
concept in the report, give more. Each round waits for the model, which on the CPU of a notebook
takes minutes, though what the person looks at is the split of the names and the terms left.

## What is decided

As the maintainer decided: `describe --without-llm` runs the steps that need no language model and
skips those that ask it.

- **Done without it:** the names split into their terms, each with its candidates; the
  abbreviations no name has dropped from the glossary, and the concepts of no term; a name read
  whose terms have one candidate each, or are of digits; a reading kept while the terms of its name
  stay as they were split; and what the overrides give, laid over by the stages that read the
  profile.
- **Skipped:** no concept is proposed of a term of none, no concept chosen of a term of several, and
  no column described. What a run with a model filled before is kept.
- `project.yml` needs no `llm` for it, and `--anew` may come with it.

## Done when

- `describe --without-llm` splits and reads the names as above, asks no model and makes none, and
  keeps what the model filled before.

## History

- **2026-11-04** — Opened, as the maintainer decided: a flag `--without-llm` of `describe`.

- **2026-11-04** — Done as decided: `describe` takes `llm: LanguageModel | None`, and without one
  its steps that ask the model ask nothing - `proposed` drops what no name has alone, `_choice`
  chooses none, `described` describes none -, so that no warning of an answer missing is given.
  On the command line, `--anew` chose one of two stages, `_describe` and `_describe_anew`, as a
  boolean that switches a function becomes two; two options independent of each other would make
  four, and are flags of one `_describe` instead, its stage made of the options of the command, so
  that argparse stays in `main` and the stages stay typed.

- **2026-11-04** — Restructured, as the maintainer agreed after the review: the steps that need no
  model are functions of the module - `_held`, the glossary without what no name has, and
  `_names_kept`, the names split anew and read by their candidates -, and those that ask it the
  class `_Asking`, which holds a model that is never None, so that no step asks whether there is
  one. Without a model, the profile is written once, at the end, as nothing is asked that a run
  interrupted would lose. The signature of `describe` stays, its workspace as well, as the
  maintainer decided.
