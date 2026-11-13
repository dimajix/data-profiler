# 66 — Detectors of JSON documents

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of text whose values are JSON documents - objects or arrays, such as payloads, settings or attributes of a row -, nor the broken documents among them, so that such a column is told to the language model as nothing but a text, and is checked for codes, enumerations and free text like any other.

## The problem

Tables of operational systems keep what has no column of its own as a JSON document in a column
of text: the payload of an event, the settings of a customer, the attributes of a product,
`{"color": "red", "sizes": [38, 40]}`. No detector of [08](08-detection.md) recognises one: a
document is no value of any pattern of the tool, and is at most taken for free text
([21](21-a-detector-of-free-text.md)) where its strings are long. A column of the database's own
type `json` is known by its type; a column of `varchar` that holds JSON is not.

Such a column often holds broken documents as well: cut off at the length of the column, written
with single quotes, by hand, or by a system that writes JSON by concatenating texts. They look like
documents and are none; a column of many of them is a column of JSON all the same, and what a
person wants to know of it is that it is one, and how much of it is broken.

What a project can do today is give a type of its own by a pattern alone, `[{[].*[]}]`: it lets
every text between brackets pass, `[draft]` and `{n/a}` among them, as a pattern cannot tell JSON
from what merely looks like it, it tells nothing of documents that are broken, and it misses every
document of more than one line, as `.` matches no line break.

## Why it matters

- **Naming.** The matches are what the language model of [10](10-the-stage-describe.md) names
  columns from; a column recognised as JSON is a payload, a document of settings or attributes,
  which no other fact of the profile says.
- **Broken documents.** The share of documents a consumer of the column cannot parse is a fact of
  its quality, which a person modelling the data has to know before relying on the column.
- **The other checks.** A column of documents is no enumeration and no key a reference points to;
  recognised, it can be left out of what does not fit it, as a column of UUIDs or dates is of
  enumerations (`SemanticType.enumerable`).

## Considerations

### Two types: what looks like JSON, and what is JSON

Two semantic types, each with its own detector, both matches of a column where each reaches its
threshold, as a column may be a match of several types, none preferred:

- **`json-like`, the heuristic:** a pattern alone, of what a document looks like - a text that
  begins with `{` or `[` and ends with `}` or `]` -, and nothing more. It recognises documents,
  broken or not, and a column whose documents are mostly broken. Its share on the table is that of
  its pattern, as of any detector of a pattern alone.
- **`json`, the exact one:** the same pattern, and a check that the value parses as a JSON object
  or array. It recognises valid documents alone, in the sample and, after the restructuring below,
  on the whole table, so that its share on the table is exact.

A column of valid documents is a match of both, of the same share; a column of broken ones a match
of `json-like` alone, or of both, of shares whose difference is the share of broken documents. The
report and the language model see both, as they see every match; that the difference is the share
of broken documents is said in the documentation of the types, not by a field of its own.

- **The alternative weighed: one type, its match of two shares** - of the values that look like
  the type and of those that are of it. It would hold the share of broken values of every checked
  type, IBANs of a wrong checksum among them, but changes the format of a match for all types, and
  leaves open which of the two shares the threshold decides by: the share of the check loses the
  column of mostly broken documents, which is the point; the share of the pattern makes a match of
  every column of 22 characters an IBAN's pattern lets pass. Two types use the concepts there are,
  and decide each by its own threshold.
- **What the heuristic pattern says.** `[draft]` and `{n/a}` begin and end with brackets as well.
  The pattern carries as much of JSON as a pattern can, so that few such texts are `json-like`:
  after `{` a `"` or `}`, after `[` a `"`, `{`, `[`, `]`, a digit, `-`, or the first letter of
  `true`, `false` or `null`, spaces and line breaks allowed between. Whether that is enough, or the
  threshold of `json-like` has to be higher than the default, is seen on the simulation.
- **The names.** `json` for what is JSON, as it is called; `json-like` for what looks like it, as
  the names of the types are written. The type of a column of Trino named `json` is in another
  field of the profile, so that the two are not mistaken.

### First, a restructuring: a check of a value verified in SQL

Today a detector's check is a function of Python, `Detector.check`, and `matching.verify` counts the
values of the table its pattern matches, `Dialect.matching(values, kind, pattern)`; what the check
refuses, SQL does not, so that the share on the table of a checked type is at least the share the
check would give (`PROFILE.md`, the field `table` of a match). For `json` to be exact on the table,
its check has to be done in SQL as well. That changes the interfaces of `detect`, the dialect and
`matching`, and is a step of its own before the types above, without a change of behaviour: no
check is done in SQL until the second step gives one.

- **The constraint.** The dialect writes every SQL statement the tool sends; `detect` knows no
  dialect, and the dialect no semantic type. A check in SQL needs a name both know.
- **The options:**
  1. **A check named.** The check of a detector becomes a `Check` of `detect`: its name and its
     function of Python. The dialect writes the expression of a check it knows,
     `Dialect.checking(values, check) -> str | None`, None of one it cannot write, whose values are
     then checked by the pattern alone, as now. `Dialect.matching` is given the detector's pattern
     and check together. The dialect stays the one place of SQL, and a dialect that cannot write a
     check loses exactness, not correctness.
  2. **A building block per check** in the dialect, `Dialect.json_document(values)`, chosen by
     `matching` for the types it knows: a special case of each type in `matching`, which is what
     the module avoids.
  3. **A check that writes its SQL**, given the dialect: `detect` would depend on `source`, which
     it does not, and a check of the tool would hold SQL, which the dialect alone holds.

  Option 1 is recommended. Its interface is to be put before the maintainer with the plan, as
  [AGENTS.md](../AGENTS.md) asks of a changed public interface.
- **What a share on the table means.** With checks in SQL, the field `table` of a match is the
  share the detector recognises on the whole table as far as the dialect checks it: exact where it
  writes the check, at least the share of the check where it does not. The format of the profile
  does not change, its documentation does - `PROFILE.md`, the module docs of `matching` and
  `detect`, and the stage `scan` in `ARCHITECTURE.md`, which says the matches are verified "by the
  patterns of the detectors in SQL".
- **Python and SQL agree.** A check done twice has to give the same answer twice. `json.loads`
  takes `NaN`, `Infinity` and `-Infinity`, which JSON does not; the check of Python refuses them.
  Duplicate keys, deep nesting and numbers beyond a double are tried on both, `json.loads` and the
  expression of Trino - `try(json_parse(...))`, or a predicate of the SQL standard where Trino has
  one -, and where they still differ, the difference is named in the tests.
- **Other types.** The check of a date could be done in SQL as well; IBANs, card numbers and phone
  numbers hardly. None of them is part of this issue: `json` is the first user of the mechanism.

### Of both types

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
- **The threshold.** Half of the values, the default, of both, unless the simulation shows that
  `json-like` needs a higher one.
- **Enumerable:** neither, as a document is no value of a closed list, even where a few repeat;
  whether that is right for a column of a handful of settings documents is to be seen on the real
  database.
- **The sensitivity.** None, as [21](21-a-detector-of-free-text.md) decided for free text: a
  document holds personal data in passing - `{"name": "Hans Müller", ...}` - which no detector of a
  value finds; an override marks a column that holds personal data. The ends of the range of such a
  column go into the profile, cut to 100 characters (`disclosure.py`), as of free text.
- **A column of the type `json`.** Trino writes its objects and arrays as JSON (`source._text`),
  so that both detectors recognise them, and its scalars without quotes, which they do not. The
  matches say nothing the type does not, but every column is checked whatever its type, and an
  exception for one type would be a special case of its own; none is made.
- **Beyond recognising a document.** What a document holds - its keys, their types, the semantic
  types of its values - would say much more of the column, but is a profile of a structure inside a
  column, as [43](43-columns-of-lists-of-values.md) made one of lists: a concept of its own, and on
  the table a query per key. It is not part of this issue; once documents are recognised, it may be
  one of its own.

### What it costs

No query of its own; the exact check on the table is what costs most:

- **In the sample**, of about 10,000 values per column, taken whole: the pattern is tried on every
  value of every column, as every pattern is; `json.loads` runs only on the values the pattern
  matches, so that a column of no documents costs a pattern more and nothing else. A column of
  documents costs a parse of each, in C, a matter of milliseconds for documents of a few
  kilobytes: an estimate, not measured.
- **On the table**, `matching.verify` adds to the one query it sends anyway, and only for a column
  that is a match in the sample, one count of `json-like`, a pattern, and one of `json`, the
  pattern and the parse. The column is read by that query in any case where it has another match;
  where JSON is its only one, the query reads it in addition. A pattern anchored at either end is
  tried once along each value. The parse costs more: it builds each document, and a broken one
  raises an error inside Trino that `try` catches, which costs more again, so that a column of many
  broken documents is the most expensive. Whether Trino parses a value the pattern refused, or
  stops at the pattern, is to be seen in the plan of the query. Both grow with the length of the
  documents, as reading them does; the times are measured on the simulation, with documents of
  several kilobytes and a share of broken ones.

## Steps

1. **A check of a value verified in SQL** - a refactoring, without a change of behaviour: `Check`,
   `Dialect.checking`, `Dialect.matching` given the pattern and the check, `matching.verify`
   counting by both; no check of the tool has an expression in SQL yet, so that every query stays
   as it is. The documentation of a share on the table changed as above.
2. **The types `json-like` and `json`**, the check of `json` written in SQL by the dialect of
   Trino, the simulation and the measurements.

## Done when

- Step 1: a detector's check has a name the dialect writes an expression of, or none;
  `matching.verify` counts the values of a check it writes by pattern and check, of the others by
  the pattern alone; every query a scan sends is as before; `PROFILE.md`, `ARCHITECTURE.md` and the
  module docs say what a share on the table now is.
- Step 2: `detect` has the built-in types `json-like`, by a pattern of what a document looks like,
  over lines as well, and `json`, by that pattern and a check that the text parses as a JSON object
  or array, written in SQL by the dialect of Trino; both of no sensitivity, not enumerable.
- A number, a flag and a string in quotes are neither; a text in brackets that does not parse is
  no `json`, and `json-like` where it looks like a document; `NaN` and `Infinity` are refused by
  Python as by Trino.
- The share of `json` on the table is that of valid documents, on Trino, in a test of a table of
  valid and broken documents.
- The patterns and the check have been tried on Trino on documents of several kilobytes and of
  several lines, in the simulation, with their times named in the history below.
- A profile of the simulation has a column of `varchar` of JSON documents, some of them broken,
  which the generator fills and a scan recognises as both types, of shares that differ by the
  broken ones, and a column of texts in brackets beside it, which is neither.

## History

2026-11-13: Opened on the maintainer's question whether a detector of JSON documents in columns
can be made, and whether it would be expensive to run. The answer recorded above: it fits the
detectors as they are, a pattern and a check of a value, and costs no query of its own; what a
document holds is left to an issue of its own.

2026-11-13: Extended on the maintainer's request, before any work on it: two detectors, a heuristic
of a pattern alone and an exact one, so that a column of broken documents is still recognised as
one of JSON and the share of broken documents can be told; and, as a step before them, the check of
a value done in SQL as well, so that the share of the exact type on the table is exact. The file
was renamed from `66-a-detector-of-json-documents.md` to its new title.

2026-11-13: Step 1 begun. The maintainer decided its interface otherwise than the options above
put it: `Dialect.matching` is renamed `Dialect.recognised` and given the detector, not its pattern
and its check, so that the dialect counts what a detector recognises and writes the check of one
inside, by no public method `Dialect.checking`; and a check is one of a closed list, `Check`, an
enum of `detect` whose members name the checks of the tool and pass a value by their functions, so
that a dialect tells the checks it writes by `match`, and no check of a test or a project is
unknown to it. `source` imports `detect` for it.
