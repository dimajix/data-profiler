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

- **2026-11-02** — A plan for option 3 proposed, not decided yet. The measure of the column is not
  a score of its own, which would make `Match.sample` mean something else for this type alone and
  could not be verified on the table, but a third part of `Detector`, beside its pattern and its
  check, so that `Detector` stays the one kind of detector:

  ```python
  @dataclass(frozen=True)
  class Detector:
      """Recognises one semantic type: by a pattern, a check of a value, and a condition of its column."""

      pattern: re.Pattern[str]
      check: Callable[[str], bool] | None = None
      column: Callable[[Sequence[str]], bool] | None = None
      """Whether the texts of a column, together, are of the type; None where each value says it alone."""
      threshold: float = 0.5
      """The share of the values of a sample of the type that makes it a match."""

      def recognises(self, value: str) -> bool: ...  # as now
      def share(self, texts: Sequence[str]) -> float:
          """The share of `texts` of the type; 0 where the column fails the condition."""
  ```

  - **The share stays a share of values:** of the values of words, which the pattern recognises,
    and which `verify` counts on the table as now; the condition of the column is judged on the
    sample alone, which the documentation of `Match.table` says. `detect` asks each detector for
    its `share`, so that the counting moves to the detector.
  - **The threshold of a type**, 0.5 unless given, replaces the one of `matching.py`, as a column
    of comments holds many short values. The pairs of [20](20-detectors-of-boolean-pairs.md) need
    both parts as well: the condition for at most two distinct values (option 3 there), the
    threshold for every value being of the pair (option 2 there). Condition and threshold are
    therefore decided for both issues together, as a refactoring of their own before either.
  - **The pattern of a value of words:** two words or more, one of them after the first in lower
    case, for instance `[^ ]*[A-Za-zÄÖÜäöüß][^ ]* +[a-zäöüß][^ ]*( .*)?`; `Hans Müller`,
    `Deutsche Bank AG` and `Hauptstr. 5` are none, `Bitte Rückruf am Montag` is one.
  - **The condition of the column**, `_free_text` in `detect.py` beside `_phone` and
    `_card_number`, measured on the texts of the sample, with thresholds to begin with: the share
    of values of words at least 0.2 (the threshold of the type), the share of words in lower case
    after the first of their value, over all values, at least 0.3, the share of letters among the
    characters other than spaces at least 0.7, against codes and numbers, and the share of
    distinct values at least 0.5, against categories of several words. Punctuation is left out:
    `Hauptstr. 5` has a full stop and a space too, and every measure more is a threshold more.
  - **Rules, not a weighted score or a classifier:** each threshold can be explained, logged and
    fitted on its own; a classifier would need labelled columns, which there are none of.
  - **`is_sensitive`** checks each value by `recognises`; if free text is personal, a value of
    words at the end of the range of any column is withheld, as the condition of the column does
    not apply to a value alone. Probably wanted, but to be decided with the sensitivity.
  - **The types of a project** stay of a pattern alone.
  - **The steps:** (1) a refactoring without a change of behaviour, `Detector.share` used by
    `detect`; (2) the condition of the column and the threshold of a type, decided with
    [20](20-detectors-of-boolean-pairs.md); (3) the type `free-text`, tested on columns of free
    text and on columns of names, addresses, products, codes and categories, which are none;
    (4) the simulation: the generator makes comments in German - sentences from templates, mixed
    with `ok`, `-` and `siehe oben` -, the round trip finds the column again and takes no column
    of names or addresses for one, and the thresholds are fitted on it and checked on the real
    database.
  - **Open:** whether condition and threshold become the concept shared with
    [20](20-detectors-of-boolean-pairs.md), and the sensitivity of free text.

- **2026-11-02** — Decided with the maintainer: the condition of a column and the threshold of a
  type become one concept for this issue and [20](20-detectors-of-boolean-pairs.md), built before
  either as the refactoring of [22](22-a-condition-of-a-column.md); and free text is, for now, of
  the sensitivity none -
  public -, an override marking a column of free text that holds personal data, so that
  `is_sensitive` withholds no value of words.
