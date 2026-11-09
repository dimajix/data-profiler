# 47 — Descriptions written as a dictionary does

**Status:** done
**Type:** feature
**Priority:** low
**Area:** Describe
**Summary:** The descriptions `describe` proposes of columns and concepts talk about the column or the word, `This column contains the serial number of a credit card`, where the information alone, `serial number of a credit card`, says the same.

## The problem

The language model answers the two questions for a description in whole sentences about the thing
described: a column `This column contains the serial number of a credit card`, a concept
`The word "default" refers to ...`. The words about the column or the word say nothing: everybody
who reads a description knows what it is the description of. What is wanted is what a dictionary
gives: the information the column or the concept holds, `serial number of a credit card`. It may be
a sentence where that is what it takes: `either "standard value" or bankruptcy, depending on the
context`.

## Why it matters

The descriptions are read in the report and in the glossary, one beside the other, where the same
opening before every one of them hides what differs. They are also shown to the language model: the
description of each concept goes into the questions for a reading and for the description of a
column, so that they take room there, and so that the form of one question shows up in the answers
to the next.

## Considerations

- **The wording of the two questions**, `concept.txt` and `description.txt`, is where the form is
  asked for. They ask for "one sentence" and "one or two sentences" today, which is what they get.
  Recommended, as nothing else has to change.
- **Examples in the question** show the form better than a rule can, but the comment of
  `concept.txt` records why the words of the glossary are not shown there: a small model shown them
  takes one of them for every term after. An example is to be tried, and watched for being copied.
- **Cutting the opening off the answer** in the code would be a second place that knows the form, a
  list of openings that is never complete, and leaves the verb and the capital behind it. Not
  recommended.
- **The word of a concept must not suffer.** `concept.txt` asks for the word and its description
  together, and the word is what the names are read by. A wording that improves the description but
  changes the words is no gain.
- **Profiles already written** keep their descriptions until `describe --anew`. Descriptions given
  in the overrides are not touched.

## Done when

- The descriptions of columns and concepts proposed by the model state the information alone, and
  are a sentence only where the information takes one.
- The trials are recorded below: the wordings tried, per model, and how the descriptions and the
  words proposed compare with today's.

## History

- **2026-11-09** — Opened, as the maintainer asked, with trials of the wording to be run on the
  simulation environment.

- **2026-11-09** — The wording is changed, after trials on the simulation environment: `describe`
  run whole on the example CRM, 94 columns and about 60 concepts, at temperature 0.

  `concept.txt` now asks for the meaning as a dictionary gives it, a short phrase, a whole sentence
  only where the meaning takes one. `description.txt` asks for what the column holds as a dictionary
  entry, names what is not to be said, and shows the names of the column and the table in words.

  What was tried on `qwen3.5:2b`, the model of the example project, and what came of it:

  - **Asking for a dictionary's form** ended the talk about the concepts, from 20 of 60 descriptions
    opening with it to none, but left 21 of the columns as `The column ...`.
  - **Examples** in the question, `serial number of a credit card`, gave short answers and were
    copied: 32 columns held the example, among them `cust_nm` and an IBAN described as a credit card
    serial number. Rejected.
  - **Asking what one value of the column is** gave phrases of the right form and wrong content:
    `a collection of office supplies` for a list price.
  - **Naming the reader**, `for a person who knows the business but not the database`, was given
    back as the description of `cust_nm`, and made the answers longer. It is left out of
    `description.txt`, and kept in `concept.txt`, where it did no harm.
  - **Naming what is not to be said** took the openings about the column from 21 to 3.
  - **`Where it was recognised as something, say what that is`** is kept for what it should bring
    the columns recognised, though answers of an IBAN stayed unsteady from one wording to the next.
  - **The names in words.** 23 of 94 answers were the harmonized name, `customer_type_code`, copied
    from the line that shows it. Shown in words none was, without a word about it in the question.
  - **A renamed key of the answer**, `definition` for `description`, tried with the wording of
    before, did not help: the answers named the column as often, and grew longer. Not kept.
  - **Asking for both meanings of a word used in two ways** brought the openings back, 10 of 64, and
    changed words. Not kept.

  | Model | Wording | Columns opening about the column | Words per column | Words per concept |
  |---|---|---|---|---|
  | `qwen3.5:2b` | before | 78 of 94 | 32.5 | 15.2 |
  | `qwen3.5:2b` | now | 2 | 4.9 | 5.6 |
  | `qwen3.5:4b` | before | 90 | 23.7 | 21.6 |
  | `qwen3.5:4b` | now | 2 | 14.5 | 6.5 |
  | `gemma4:e2b` | before | 81 | 14.0 | 16.2 |
  | `gemma4:e2b` | now | 5 | 5.1 | 8.8 |
  | `lfm3:1.7b` | before | 80 | 34.7 | 31.3 |
  | `lfm3:1.7b` | now | 5 | 30.6 | 11.7 |

  Judged by the agent on `qwen3.5:2b`, right / usable / wrong, the columns were 42 / 26 / 26 before
  and are 59 / 13 / 22 now: the long sentences made up the meanings of codes and asides of phone
  numbers and postal codes. Four went from right to wrong: `ord.iban`, `prtnr.bnk_acct`,
  `cust.crdt_lmt_amt` and `ord_itm.unt_prc_amt`.

  The words of `qwen3.5:2b` changed for 9 terms of 72, seven of them for the better (`sts` from
  `stock` to `status`, `actv` from `customer` to `active`), `scr` and `uuid` wrong before and after.
  `qwen3.5:4b` changed 2 and `gemma4:e2b` 4, among them `frm` from `from` to `form` and `crt` from
  `created` to `credit`, for the worse. `lfm3:1.7b` changed 13, wrong before and after for most.

  Not reached: none of the four models gave both meanings of `default`, shown it in a loan and in a
  configuration, by this wording, nor `qwen3.5:2b` by the two wordings that asked for them. The
  question allows a sentence where it is needed, but the sentence wanted did not come.

- **2026-11-09** — Done, as the maintainer accepted it: a word of two meanings is left to a
  description given in the overrides.
