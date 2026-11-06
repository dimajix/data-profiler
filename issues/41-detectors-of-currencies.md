# 41 — Detectors of currencies

**Status:** open
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
