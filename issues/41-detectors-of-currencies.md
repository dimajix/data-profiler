# 41 — Detectors of currencies

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of currencies - written as the alphabetic code of ISO 4217, `EUR`, as its number, `978`, or by its English name, `Euro` -, so that a currency is told to the language model as nothing but a text or a number.

## The problem

The detectors of the tool recognise e-mail addresses, phone numbers, postal codes, IBANs, card
numbers, dates, UUIDs, free text and flags. A column of currencies - beside an amount, in an order,
a price or a payment - is of none of them: `EUR` is told to the language model as a text of three
letters, `978` as a number, `Euro` as a word. That the column holds currencies, which tells what the
amounts beside it are, has to be guessed from its name alone.

## Why it matters

A currency is one of the columns most often found beside an amount, and its name is often of no
help: `cur`, `wcd`, `curr_cd`. A semantic type of it tells the language model what the column holds,
and the reader of the report which columns of amounts have a currency beside them.

## What is decided

As the maintainer decided:

- **Three semantic types**, one of each way a currency is written, as the flags are a type of each
  pair: `currency-code`, the alphabetic code of ISO 4217, `EUR`; `currency-number`, its number,
  `978`; and `currency-name`, its English name, `Euro`. Each of the sensitivity `none`.
- **The currencies are those of `pycountry`**, a dependency of its own, which holds the 178 current
  currencies of ISO 4217 with their codes, numbers and English names, and is kept up with the
  standard - **and the historic ones beside them**, as an old database may well hold `DEM`, `FRF` or
  `ITL`. `pycountry` holds no historic currencies: they are a list of the tool's own.
- **The pattern is the alternation of the codes, the numbers or the names**, so that it carries the
  whole check, and the whole table is checked in SQL by it alone; a detector of a currency needs no
  check of a value.

As the maintainer decided on the questions below, and on the plan of the work:

- **Numbers** are a match where 95 percent of the values are numbers of currencies - a few values
  amiss allowed, which a threshold of every value, as of the flags, would not -, and only of three
  digits: `8` is no `008`, as small whole numbers are too common.
- **Names** are those of ISO 4217 and a list of more common names of the tool's own -
  `British Pound`, `Albanian Lek` -, each as written, in lower case, with a capital and in
  capitals. Codes are in capitals alone, as ISO 4217 writes them.
- **The historic currencies** are those withdrawn from ISO 4217 since the euro, 1999, of its list of
  withdrawn currencies: `DEM`, `FRF`, `HRK`, `VEF` and the others, not those before.
- **Codes that are words** have the threshold of half the values, as hardly a column holds such
  codes alone.
- **A module of its own, `currencies`**, holds the codes, numbers and names, as three tuples, not a
  class of a currency, which nothing would use but to make them; the simulation takes its values
  from them. `XTS`, the code of testing, and `XXX`, of no currency, are left out, as `XXX` stands
  for an unknown value in many a column.
- **The version of the profile** is raised from 14.1 to 14.2, so that a tool older than a profile
  of a currency names itself older, rather than refusing an unknown semantic type.
- **The example profile** marks `ord.curr_cd` a column of codes, and has `prod.prc_curr_no` of
  numbers and `cust.curr_nm` of names beside it.
- **Two steps**: first `_cases` of `detect` and `_pair` of the simulation generalised to words of
  any case - `cases` writes a word as written, in lower case, with a capital and in capitals -,
  without a change of behaviour; then the detectors.

## What is to be decided

- **Numbers.** About a fifth of the numbers from 000 to 999 are numbers of currencies, so that a
  column of quantities or of codes of status would be taken for one by half of its values. A
  threshold of every value, as of the flags, would keep them apart. And a column of integers writes
  `8`, not `008`, the lek: whether a number below 100 is recognised without its leading zeros as
  well - 16 currencies have one -, at the risk of more columns of small numbers taken for
  currencies.
- **Names.** The English names of ISO 4217 are partly unusual - `Lek`, `Taka`, `Afghani`,
  `Pound Sterling` -, so that the names a database is likelier to hold, `British Pound`,
  `Albanian Lek`, would be missed. Whether the names of ISO 4217 alone are recognised, in lower
  case, as written and in capitals, as `_cases` writes those of the flags, or more names beside them
  of a list of the tool's own.
- **Which historic currencies**: those of ISO 4217 withdrawn, all of them, or those replaced by the
  euro alone, of the codes, numbers and names of each.
- **Codes that are words.** Some codes are words or abbreviations in capitals as well - `ALL`,
  `TOP`, `PEN`, `TRY`, `SOS`, `CUP` -; whether the threshold of half the values is enough to keep a
  column of such words apart, or the codes need more, such as a threshold of their own.

## Done when

- A column of currencies written as codes, as numbers or as English names is matched by its type,
  in a sample and on the whole table, the historic currencies decided among them.
- A column of quantities, of codes of status, or of other words in capitals is not, as decided.
- The simulation environment holds columns of each of the three types, and its test data generator
  writes them, as it does the other types of the tool, so that each is recognised on the database.
- The semantic types of the tool are described with the three in the documents where they are
  listed.

## History

- **2026-11-06** — Opened, as the maintainer asked: three detectors of currencies, of the codes,
  numbers and English names of `pycountry`, with the historic currencies beside them.

- **2026-11-06** — Step 1 done: `cases` in `detect` writes a word in each of its cases, of which
  `_cases` makes a pattern, its characters escaped; the flags `true`/`false` and `yes`/`no` match
  as they did, and `zero-one` is made by `_cases` too, `0|1` in place of `[01]`, which match alike.
  `_one_of` of the simulation, in place of `_pair`, chooses one of the spellings it is given - the
  `cases` of a word, or codes as written -, so that one generator serves the flags and the
  currencies; the values of the columns of `yes`/`no` and `0`/`1` it makes are spread otherwise
  than before, with the same statistics.
