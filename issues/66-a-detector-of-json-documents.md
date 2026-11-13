# 66 — A detector of JSON documents

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of text whose values are JSON documents - objects or arrays, such as payloads, settings or attributes of a row -, so that such a column is told to the language model as nothing but a text, and is checked for codes, enumerations and free text like any other.

## The problem

Tables of operational systems keep what has no column of its own as a JSON document in a column
of text: the payload of an event, the settings of a customer, the attributes of a product,
`{"color": "red", "sizes": [38, 40]}`. No detector of [08](08-detection.md) recognises one: a
document is no value of any pattern of the tool, and is at most taken for free text
([21](21-a-detector-of-free-text.md)) where its strings are long. A column of the database's own
type `json` is known by its type; a column of `varchar` that holds JSON is not.

What a project can do today is give a type of its own by a pattern alone, `[{[].*[]}]`: it lets
every text between brackets pass, `[draft]` and `{n/a}` among them, as a pattern cannot tell JSON
from what merely looks like it, and it misses every document of more than one line, as `.` matches
no line break.

## Why it matters

- **Naming.** The matches are what the language model of [10](10-the-stage-describe.md) names
  columns from; a column recognised as JSON is a payload, a document of settings or attributes,
  which no other fact of the profile says.
- **The other checks.** A column of documents is no enumeration and no key a reference points to;
  recognised, it can be left out of what does not fit it, as a column of UUIDs or dates is of
  enumerations (`SemanticType.enumerable`).

## Considerations

**The closest pattern: a detector of a pattern and a check of a value**, as `IBAN`, `PHONE` and
`DATE` are. The pattern carries what a pattern can - an object or an array, a text that begins
with `{` or `[` and ends with `}` or `]` -; the check parses the value, `json.loads`, and takes it
where it is an object or an array. No new concept is needed: `Detector(pattern, check)` covers it.

- **Objects and arrays only.** A number, `true`, `null` and a string in quotes are JSON too; taken,
  every column of numbers or flags would be one of JSON. A document is an object or an array.
- **The pattern across lines.** A document written over several lines is one value as well. `.`
  matches no line break, in Python as in SQL, and the patterns use no flags and no escapes but of a
  character, so that what matches any character, a line break included, is to be found: a class
  repeated (as `_OF_WORDS` uses `[^ ]` to let a word hold a line break), an alternative of two
  classes that together match every character, `(.|[^.])*`, or a flag the dialect writes, which
  would be a concept of its own. How the regular expressions of Trino fare on an alternative
  repeated over a value of several kilobytes is to be measured on the simulation, not assumed; a
  plain class repeated is preferred where one does.
- **The share on the table.** `matching.verify` counts the values of the whole table the pattern
  matches; the check is not done in SQL, so that the share on the table is that of texts between
  brackets, at least the share of documents, as it is of IBANs and phone numbers. The check could be
  done in SQL too, `try(json_parse(...)) IS NOT NULL` in Trino, but that would be the first detector
  verified by more than its pattern - a change of `Detector` and the dialect for all types, not
  for this one.
- **The threshold.** Half of the values, the default: a value that parses as an object or an array
  is JSON by no chance, so that a lower or a higher threshold is not needed.
- **Enumerable:** no, as a document is no value of a closed list, even where a few repeat; whether
  that is right for a column of a handful of settings documents is to be seen on the real database.
- **The sensitivity.** None, as [21](21-a-detector-of-free-text.md) decided for free text: a
  document holds personal data in passing - `{"name": "Hans Müller", ...}` - which no detector of a
  value finds; an override marks a column that holds personal data. The ends of the range of such a
  column go into the profile, cut to 100 characters (`disclosure.py`), as of free text.
- **A column of the type `json`.** Trino writes its objects and arrays as JSON (`source._text`),
  so that the detector recognises them, and its scalars without quotes, which it does not. The
  match says nothing the type does not, but every column is checked whatever its type, and an
  exception for one type would be a special case of its own; none is made.
- **The name of the type:** `json`, as it is called; the type of a column of Trino of that name is
  in another field of the profile, so that the two are not mistaken.
- **Beyond recognising a document.** What a document holds - its keys, their types, the semantic
  types of its values - would say much more of the column, but is a profile of a structure inside a
  column, as [43](43-columns-of-lists-of-values.md) made one of lists: a concept of its own, and on
  the table a query per key. It is not part of this issue; once documents are recognised, it may be
  one of its own.

### What it costs

Little, as it follows the pattern of the detectors and adds no query:

- **In the sample**, of about 10,000 values per column, taken whole: the pattern is tried on every
  value of every column, as every pattern is; `json.loads` runs only on the values the pattern
  matches, texts between brackets, so that a column of no documents costs a pattern more and
  nothing else. A column of documents costs a parse of each, in C, a matter of milliseconds for
  documents of a few kilobytes - an estimate, not measured.
- **On the table**, `matching.verify` adds one `count_if(regexp_like(...))` to the one query it
  sends anyway, and only for a column that is a match in the sample. The column is read by that
  query in any case where it has another match; where JSON is its only one, the query reads it in
  addition. A pattern anchored at either end is tried once along each value, so that the cost grows
  with the length of the documents, as reading them does; how an alternative repeated behaves there
  is the measurement above.

## Done when

- `detect` has a semantic type `json`, recognised by a pattern of a text between brackets, over
  lines as well, and a check that the text parses as a JSON object or array; it is a built-in
  type, of no sensitivity, not enumerable.
- A number, a flag, a string in quotes and a text in brackets that does not parse are none.
- The pattern has been tried on Trino on documents of several kilobytes and of several lines, in
  the simulation, with its time named in the history below.
- A profile of the simulation has a column of `varchar` of JSON documents, which the generator
  fills and a scan recognises, and a column of texts in brackets beside it, which it does not.

## History

2026-11-13: Opened on the maintainer's question whether a detector of JSON documents in columns
can be made, and whether it would be expensive to run. The answer recorded above: it fits the
detectors as they are, a pattern and a check of a value, and costs no query of its own; what a
document holds is left to an issue of its own.
