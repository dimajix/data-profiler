# 04 — Can a small local model name columns?

**Status:** in progress
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

- **2026-10-30** — The trial is prepared, as the maintainer decided: in the dev container of
  [14](14-a-dev-container.md), by a script in a directory of its own, `work/`, checked in.
  `work/naming_trial.py` plays `describe` on an environment `scan` has profiled, from the
  profile with the overrides laid over it and the samples of the workspace: first the word of each
  term of the names of the columns chosen, shown where it appears, then the name and description
  of each column, given the words and the name they compose, each through Ollama with a JSON schema
  as `format`. The answers go into the workspace, each with its time and an empty judgement, and
  `--summary` counts the judgements, which alone go into this issue. The first model tried is
  `lfm3:1.7b`, which the maintainer chose.

- **2026-10-30** — A trial run on the simulation environment, not on the real database, judged by
  the agent, who knows what the abbreviations of the example stand for: 52 terms, then the names of
  52 columns, each counted right / usable / wrong. Thinking is off: with it, `lfm3:1.7b` took 193
  seconds for one word, and found it wrong. In the second round, the question for a term showed
  each of its columns with its type, its matches and a few values, and said that an abbreviation is
  mostly the word shortened.

  | Model | Round | Terms | Names of columns |
  |---|---|---|---|
  | `lfm3:1.7b` | 1 | 34 / 2 / 16 | 25 / 12 / 15 |
  | `lfm3:1.7b` | 2 | 32 / 5 / 15 | 31 / 6 / 15 |
  | `qwen3.5:2b` | 1 | 38 / 3 / 11 | 42 / 3 / 7 |
  | `qwen3.5:2b` | 2 | 43 / 3 / 6 | 45 / 3 / 4 |

  `qwen3.5:2b` does clearly better: `lfm3:1.7b` fills in a word of the surroundings where it does
  not know one - `customer` for `crt`, `curr` and `seg` -, and gains nothing from more facts, which
  help `qwen3.5:2b`. Terms first and columns second works, but an error goes on: both take `crt` for
  `customer`, and name `crt_dt` `customer_date`, as a model hardly changes the name the words
  compose. One word per term does not hold everywhere: `lst` is "last" in `lst_nm` and "list" in
  `lst_prc_amt` - for [10](10-the-stage-describe.md) to settle. The descriptions make up meanings of
  the random codes of the simulation, so that only the real database can judge them. Each model took
  40 to 50 seconds for all, on the Ollama of the machine of the agents, which says little of the
  Intel CPU of the dev container. The run on the real database is the maintainer's.
