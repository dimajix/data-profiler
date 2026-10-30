# 04 — Can a small local model name columns?

**Status:** open
**Type:** question
**Priority:** high
**Area:** Describe
**Epic:** [02](02-first-version-epic.md)
**Summary:** Nobody knows yet whether a language model of 1 to 2 billion parameters, running locally, names columns well enough from prepared facts - and the stage describe rests on it.

## The problem

The design leaves the language model one task: to propose a word for each term of the original names
and a name and a description for each column, from facts the detectors and the statistics prepared
(`docs/ARCHITECTURE.md`, "Detectors decide, the language model names"). It has to run in Ollama on a
notebook with 32 GB of memory, so it is small - LFM2 of Liquid AI, Qwen3 of 1.7 or 4 billion
parameters, Gemma 3 of 1 or 4 billion. Whether such a model does the task well enough is not known.

## Why it matters

It is the largest risk of the first version. If the answer is no, [09](09-the-glossary.md) and
[10](10-the-stage-describe.md) are built differently - with a larger model, with smaller questions,
or with the glossary written by hand and the model only for descriptions. Finding that out after
building them costs both.

## How

A trial by hand, without code in the repository, by the maintainer on the machine that can read the
real database; the data stays there.

1.  Pick about 20 columns of the CRM, among them several dates and several columns whose names
    share abbreviations.
2.  Write down the facts for each as `describe` would give them: table name, column name, type,
    null share, distinct count, the values of an enumeration, what a detector would find, the
    names of the columns beside it, a few sample values.
3.  Ask each model, through Ollama with a JSON schema as `format`, first for the word of each
    abbreviation, shown the columns it appears in, then for the name and description of each
    column, given the words.
4.  Judge the answers: right, usable after correction, wrong.

## Done when

The results are recorded under History - per model: how many answers were right, usable or wrong,
and how long it took -, and the decision for [10](10-the-stage-describe.md) is taken: which model,
whether terms first and columns second works, and what the prompt has to contain.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).
