# 47 — Descriptions written as a dictionary does

**Status:** open
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
