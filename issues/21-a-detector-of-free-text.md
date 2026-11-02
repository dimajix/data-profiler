# 21 — A detector of free text

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of free text - comments, notes, descriptions -, so that it is told to the language model as a text like any other, and its values are disclosed like those of a code.

## The problem

Every detector of [08](08-detection.md) recognises a value on its own, by a pattern it matches
whole; a type is a match of a column where half of the values of the sample or more are of it.
Free text is not a form of a value but a property of a column: a column of comments holds
sentences, but also `ok`, `siehe oben` and `-`, and a value of several words is not free text by
itself - a name `Hans Müller`, an address `Hauptstr. 5`, a product `Deutsche Bank AG` are of
several words, and a column of them is none. What tells free text apart is seen in the values
together: many words, words in lower case, punctuation, values that hardly ever repeat and differ
much in length.

## Why it matters

- **Naming.** The matches are what the language model of [10](10-the-stage-describe.md) names
  columns from; a column recognised as free text is a comment, a note or a description, which no
  other fact of the profile says.
- **Disclosure.** Free text holds personal data in passing - `Hr. Müller bittet um Rückruf unter
  0171 …` -, which no detector of a value finds, as none matches a part of a value. The ends of
  the range of such a column go into the profile, cut to 100 characters (`disclosure.py`).

## Signs of free text

Of a value:

- **Words:** runs of letters, separated by spaces; free text has several, a code or a name few.
- **Words in lower case** after the first: prose has them - in German too, its articles,
  prepositions and verbs -, a name, an address or a title of a product mostly not.
- **Punctuation** followed by a space or at the end: `,`, `.`, `!`, `?`.
- **Letters** making most of the characters, against codes and numbers.

Of the column:

- **The share of values of words**, as defined above; it need not be half, as short values are
  frequent in a column of comments.
- **Distinct values:** nearly as many as values, `distinct` of the statistics against the values
  that are not null; and no enumeration.
- **Lengths:** a longest value of many characters, and a wide range between shortest and longest,
  both counted by the statistics already.

## What is to be decided

- **How a column is judged.** The options:
  1. **A pattern of a value alone**, as every type now: a value of two words or more, one of them
     in lower case. It fits the detectors and is verified on the table like them, but misses
     every column of comments in which short values are the half or more, as the threshold of
     `matching.py` is one for all types.
  2. **A pattern of a value and a condition of its column.** The share of the values the pattern
     recognises is weighed against a threshold of the type, lower than one half, and the column has
     to meet a condition of its statistics - many distinct values, a long longest value. The
     share is verified on the table by the pattern as now; the statistics are counted anyway. It
     costs a concept the detectors do not have yet, a condition of a column, which the pairs of
     [20](20-detectors-of-boolean-pairs.md) need as well (option 3 there: at most two distinct
     values), and a threshold of each type instead of one for all.
  3. **A measure of the column from the sample:** the signs above averaged over the values -
     words per value, the share of words in lower case, of punctuation, of letters - and weighed
     together. The most exact, but nothing of it is verified on the table by a pattern, so that
     the share of the match on the table means something else for this type, or is missing.
- **The language.** Words in lower case are written as classes of letters, as the patterns are
  shared by Python and SQL and share no class of Unicode; the letters of German and English,
  `[a-zäöüß]`, are enough for the databases at hand, and a list of frequent words of a language
  is not needed if the case of the words says enough.
- **The thresholds:** how many words, which share of values of words, which share of distinct
  values, which longest value. They are fitted on the simulation and checked on the real database.
- **The sensitivity.** None, as sensitivity is judged optimistically, an override marking a
  column of free text that holds personal data; or personal, as free text is where personal data
  hides from every detector, and its values are not needed to name the column - the type says
  enough.
- **The name of the type,** for instance `free-text`; `text` alone is mistaken for the type of a
  column of the database.
- **The simulation.** A column of free text in the example of the simulation - sentences in
  German, beside short values -, which the generator fills, and columns of names, addresses and
  products of several words beside it, which are no match.

## Done when

- The detector is tested on columns of free text and on columns of names, addresses, products and
  codes, which are none.
- In the round trip, the column of free text of the example is found again, and no column of
  names, addresses or products is taken for one.

## History

- **2026-11-02** — Opened as the maintainer asked for a detector of free text, judged by the
  values of a column together: their words, punctuation and spaces, and a statistic of the whole
  column, as not every value of free text is of several words.
