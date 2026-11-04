# 30 — Abbreviations given that no name has

**Status:** done
**Type:** bug
**Priority:** high
**Area:** Profile
**Summary:** An abbreviation the overrides give that no name of the profile has ends `describe` and `report` with an error, though the overrides are the same for all environments of a project and its glossary may well hold terms of tables that one environment does not have, or not yet.

## The problem

The overrides refuse an abbreviation of a concept given that no name of the profile has
([27](27-glossary-of-concepts.md)): `Overrides.laid_over` raises an `OverridesError`, and the stage
that lays them over - `describe` or `report` - ends. The overrides of a project are one document for
all its environments, and its tables are selected by a pattern; a glossary is written for the
domain, often before the names of one database are known. An abbreviation that the profile of one
environment does not have is therefore no mistake, and a person cannot keep one glossary for all.

## Why it matters

The glossary is to be built once and grow: a person giving the terms of a domain should not have to
take out every abbreviation one environment lacks, and put it back for the next.

## What is decided

As the maintainer decided: an abbreviation given that no name has is no error, but a warning, and
the stage goes on. What a warning still catches is a term given in another case than the names
have, `CUST`, which matches no term of a name, as terms are in lower case.

## What is to be decided

- **Where the warning is given.** `describe` lays the overrides over its profile at each of its
  steps, five times a run; a warning given by `Overrides.laid_over` would be given as often.

## Done when

- An abbreviation given that no name has is named in a warning, once a stage, and the stage goes
  on.

## History

- **2026-11-04** — Opened, as the maintainer decided: an abbreviation given that no name has is to
  be a warning, not an error.

- **2026-11-04** — Done as the maintainer decided: `Overrides.warn_unused` warns of the
  abbreviations given that no name of a profile has, naming them, and `describe` and `report` call
  it once before they lay the overrides over; `Overrides.laid_over` no longer refuses them. It
  takes back what [27](27-glossary-of-concepts.md) decided, "an abbreviation no name has is
  refused". A word given that no name has is warned of no more than it was refused, since
  [29](29-the-word-of-a-concept-as-a-term.md).
