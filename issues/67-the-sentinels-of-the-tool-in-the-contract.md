# 67 — The sentinels of the tool in the contract

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Export
**Summary:** The data contract writes, of every column of no nulls and no sentinels found, a rule against all the sentinels of the tool its type can hold - `''`, `NULL`, `null`, `N/A`, `n/a`, `-` of every column of text, the six forms of the first and the last day of every date -, although neither the overrides nor the data name them, so that the contract is full of sentinels nobody gave and nothing holds.

## The problem

The contract of [57](57-export-as-open-data-contract.md) writes, of a column that holds no nulls
and in which no sentinels were found, a rule that it holds none of its sentinels:
`Contract._missing` in `src/data_profiler/contract.py` (around line 222), a quality rule of the
metric `missingValues`, `mustBe: 0`. Its sentinels are those given of the column by an override,
else those of the tool, `detect.SENTINELS`, of them those its type can hold, as the dialect tells
(`Dialect.held`).

Of a column given no sentinels, the rule therefore lists every sentinel of the tool its type can
hold: of every column of text the twelve values of `SENTINELS`, of a `date` or a `timestamp`
`0001-01-01`, `1900-01-01` and `9999-12-31`, of a `json` all twelve as texts. A contract of a
schema of a few hundred columns of text repeats the same twelve values a few hundred times. They
are a default of the tool - what it looks for, as it knows of no others - and say nothing of the
column: no person gave them, and none was found in it.

The sentinels found are in the contract already, elsewhere: they are taken as values of their
column, which they are counted without, so that the enumeration, the lengths, the range and the
pattern of a semantic type hold of the rows they were observed of
([60](60-the-range-of-times-in-the-contract-is-not-widened-to-their-sentinels.md)), and the
experts see them to forbid. A column of sentinels found has no rule `missingValues`: `mustBe: 0`
would be broken by those rows.

The profile is not concerned: it holds the sentinels given of a column, `Column.sentinels`, and
those found in it, `Statistics.sentinels`, but none of the tool that were not found.

## Why it matters

The contract is a basis that experts extend and rework into what is binding, by hand. Every rule
of it is read and judged by them; a rule that repeats a default of the tool in every column buries
the rules that say something of the column - the sentinels a person gave of it, and those found in
it - and makes them remove, column by column, what no one asked for. A rule `missingValues` of
`N/A` of a column of order numbers tells as little as one of `N/A` of a column of numbers, which
[59](59-sentinels-given-that-a-type-cannot-hold.md) and 57 already leave out.

## Considerations

**Which sentinels go into the contract.** The maintainer's wish: those given of a column by an
override, and those found in it - not those the tool would have looked for.

- **The sentinels found** are in the contract as values today, and stay so: a rule that the column
  holds none of them would be broken by the rows they were found in, and a rule that counts them -
  `mustBeLessOrEqualTo` of their rows - is quantitative, which 57 rejected. ODCS has no rule
  `missingValues` without an operator: the JSON schema of the standard requires one of a library
  rule (`DataQualityOperators`), so that a list of the missing values that is no rule cannot be
  written in a library rule either. Open: whether the sentinels found are to be named as such
  beyond being values - in the `description` of the rule, or in `customProperties` of the column,
  the sentinels found with their name, without a rule -, so that an expert sees which values of an
  enumeration or which end of a range are sentinels.
- **The sentinels given** keep their rule, of those its type can hold, where none was found.
  Open: whether a column of some of its sentinels given found gets a rule of the others given,
  those not found. Today it gets none, as any sentinel found takes the rule away; a rule of those
  not found would say what holds of every row, as 57 asks of a rule, and is what a person who gave
  them meant.
- **The sentinels of the tool** not found go into the contract nowhere. A column given no
  sentinels and holding no nulls is `required` and has no rule `missingValues`.

**What it costs.** A contract of fewer rules: a column that holds no `''` and no `N/A` today says
so, and will not; an expert who wants the rule writes it, or gives the sentinels of the column in
the overrides, from which the contract then writes it. `Contract._missing` takes the sentinels
given alone, so that `detect.sentinels`, which chooses between those given and those of the tool,
loses its use in `contract`; it stays for `statistics` and the dialect, which look for those of
the tool. The tests of the rule of sentinels in `tests/test_contract.py` change with it, and the
documents that say "of no sentinels where none were found": the module docs of `contract` and
`docs/ARCHITECTURE.md`, the stage `export`.

## Done when

The contract writes no sentinel of the tool that was neither given of its column nor found in it:
a rule `missingValues` holds the sentinels given of the column alone, of those its type can hold;
the sentinels found are in the contract as values, as they are; the open questions above are
decided; the documents say so, and the tests show it.

## History

2026-11-23: Opened on the maintainer's request: a contract exported lists all the sentinels of the
tool a column can hold, as the type of the column decides; it is to list only those given by an
override, or found in the data. The analysis found that the sentinels found are written as values
already, and that those of the tool reach the contract by the rule `missingValues` alone, decided
in 57.
