# 42 — Detectors of countries

**Status:** in progress
**Type:** feature
**Priority:** medium
**Area:** Detection
**Summary:** Nothing recognises a column of countries - written as a code of ISO 3166-1 of two letters, `DE`, or of three, `DEU`, as its number, `276`, or by its name, `Germany` -, so that a country is told to the language model as nothing but a text or a number.

## The problem

The detectors of the tool recognise e-mail addresses, phone numbers, postal codes, IBANs, card
numbers, dates, UUIDs, free text and flags, and - once [41](41-detectors-of-currencies.md) is done -
currencies. A column of countries - of an address, a customer, a supplier, a bank - is of none of
them: `DE` and `DEU` are told to the language model as texts of letters, `276` as a number,
`Germany` as a word. That the column holds countries has to be guessed from its name alone, which is
often of no help: `lnd_cd`, `ctry`, `iso2`.

## Why it matters

A country is one of the columns most often found in an address, beside the postal code, which the
tool recognises as German alone. A semantic type of it tells the language model what the column
holds, and the reader of the report which tables hold addresses of which countries.

## What is wanted

As the maintainer asked: detectors of countries as those of currencies of
[41](41-detectors-of-currencies.md) - of their codes, numbers and names -, made the same way:

- **A semantic type of each way a country is written**: the code of two letters, `DE`; the code of
  three letters, `DEU`; the number, `276`; and the English name, `Germany`. Each of the sensitivity
  `none`, as a country alone identifies no person.
- **The countries of `pycountry`**, which holds the 249 countries of ISO 3166-1 with their codes,
  numbers and English names, and the 31 withdrawn of ISO 3166-3 - `DDR`, `CSK`, `SCG`, `ANT` -,
  beside a list of more common names of the tool's own, as for the currencies.
- **The pattern is the alternation of the codes, the numbers or the names**, so that it carries the
  whole check, and the whole table is checked in SQL by it alone.
- **Numbers** of three digits alone, `40` no `040`, Austria, and a match where 95 percent of the
  values are numbers of countries, as for the currencies.

## What is decided

As the maintainer decided on the questions below, and on the plan of the work:

- **Four semantic types**, one of each way a country is written: `country-alpha-2`, the code of two
  letters of ISO 3166-1, `DE`; `country-alpha-3`, the code of three letters, `DEU`;
  `country-number`, its number, `276`; and `country-name`, its English name, `Germany`. Each of the
  sensitivity `none`. The codes are named alpha-2 and alpha-3, as ISO 3166 names them, since a
  country has two codes, where a currency has one, `currency-code`.
- **Codes of two letters** are a match where 95 percent of the values are codes, as the codes and
  the numbers of currencies are, with no condition of the column: a column of flags `YES`/`NO` or
  of codes of languages is none unless nearly every value is a country, and a condition such as
  more than two distinct values would refuse a column of countries holding `DE` and `AT` alone.
  So are codes of three letters and numbers, the numbers of three digits alone. Codes are in
  capitals alone, as ISO 3166 writes them.
- **Names in English alone**, as the system is English: no names in German or other languages.
- **The names of ISO 3166** are the name of each country, its official name and its common name,
  where `pycountry` gives them, beside a list of more common names of the tool's own - `USA`,
  `Great Britain`, `Russia`, `Soviet Union` -, each as written, in lower case, with a capital and
  in capitals, a match where half the values are names. No name is left out as a word of other
  columns, as no column holds `Chad`, `Jordan` or `Georgia` in half of its values.
- **The withdrawn countries** are all those of ISO 3166-3, of their codes, numbers and names, as the
  countries an old database is likeliest to hold were withdrawn before 1999: `DDR`, `SUN`, `CSK`.
- **Countries and currencies overlap** and are both reported: a column of values of both is a match
  of both types, and whoever models the data decides which it is.
- **A module of its own, `countries`**, holds the codes, numbers and names, as four tuples, as the
  currencies are in `currencies`.
- **Two steps**: first `detect` and the simulation tell the tuples of the currencies apart by their
  module, `currencies.CODES`, as those of the countries are named alike, without a change of
  behaviour; then the detectors.

## What is to be decided

- **Codes of two letters.** Of the 676 pairs of capitals, 249 are countries, and many are words or
  other codes as well: `NO`, `DE`, `IT`, `IN`, `IS`, `AT`, `BE`, `ME`, `US`, `TO`. A column of flags
  `YES`/`NO` holds half its values of Norway, and so reaches the threshold of half the values; so
  may a column of codes of languages, of states, of departments. A threshold of their own, as of the
  numbers, or a condition of the column - more than two distinct values, say - is to be decided.
- **Names in German.** A database of a German company holds `Deutschland`, `Österreich`,
  `Schweiz` more likely than their English names. `pycountry` gives the names of other languages by
  the translations of its package `iso-codes`, by `gettext`. Whether the German names are
  recognised as well - as a type of their own, or as names of the same type - and whether other
  languages follow.
- **Which names of ISO 3166.** `pycountry` gives each country its name, `Korea, Republic of`, and
  some an official name, `Federal Republic of Germany`, or a common name, `South Korea`. Which of
  them are recognised, beside the list of the tool's own.
- **Which withdrawn countries**: all of ISO 3166-3, as an old database may well hold `DDR` or
  `YUG`, or those withdrawn since 1999 alone, as for the currencies.
- **Countries and currencies overlap.** 118 numbers of currencies are those of their countries -
  `756` is Switzerland and its franc -, and four codes of three letters are both: `BTN`, `CHE`,
  `MKD`, `SLE`. A column of such values is a match of both types, as more hypotheses are better
  than fewer; whether that is enough, or one of them is to be preferred where both match.
- **Where the countries are kept**: in a module of their own, `countries`, as the currencies are in
  `currencies` of [41](41-detectors-of-currencies.md), or both in one module of the codes of ISO,
  whose one sentence would then be the codes of ISO standards.

## Done when

- A column of countries written as codes of two or three letters, as numbers or as names is matched
  by its type, in a sample and on the whole table, the withdrawn countries decided among them.
- A column of flags `YES`/`NO`, of quantities, or of other codes of two letters is not, as decided.
- The simulation environment holds columns of each type, and its test data generator writes them,
  as it does the other types of the tool, so that each is recognised on the database.
- The semantic types of the tool are described with these in the documents where they are listed.

## History

- **2026-11-06** — Opened, as the maintainer asked: detectors of the names and codes of countries,
  as those of currencies of [41](41-detectors-of-currencies.md).

- **2026-11-06** — Decided, as recorded under *What is decided*.

- **2026-11-06** — Step 1 done: `detect`, the generator of the simulation and its test import the
  module `currencies` and name its tuples by it, `currencies.CODES`, without a change of behaviour.
