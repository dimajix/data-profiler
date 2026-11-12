# 62 — A scan drops the references of the tables it counts anew

**Status:** done
**Type:** feature
**Priority:** medium
**Area:** Scan
**Summary:** A scan drops the references and reference candidates of every table it counts anew, but keeps those of the other tables to it, so that a profile scanned again has no references of the tables counted until relate runs again, though they were only possibly outdated, as those kept are.

## The problem

`Profile.updated` in `src/data_profiler/profile.py` puts a table a scan counted anew in place of the
one of the same name. It keeps what `describe` filled of the old table (`_described`), but not its
references and reference candidates, as [35](35-references-between-tables.md) decided: "`scan`
drops the references and candidates of a table it counts anew; those of others to it stay until
`relate` runs again". The principle in `docs/ARCHITECTURE.md` names the reason in one clause:
references "are of the values of two tables", so that a table counted anew has none.

That reason holds of both directions alike, yet only one is dropped: the references of the other
tables to a table counted anew depend on its values just as much, and are kept - dropped only where
they refer to a column it no longer has. A scan that finishes a run and begins a new one counts
every table anew, so that after it the profile has no references at all, and `relate` has to run
again before the report or the contract shows any.

## Why it matters

`relate` queries the whole database and may take long; a scan run again, for a changed override or
a new table, should not lose what it found. A reference that may be outdated until `relate` runs
again is worth more to the maintainer than none.

## Considerations

- **Keep both directions** (decided): a table counted anew keeps its references and reference
  candidates, but those of a column it no longer has, as the references to it are kept but those to
  a column it no longer has. The rule gets simpler: every attribute of the profile is kept by the
  steps that do not fill it, without an exception for the references. `relate` reads no references
  of the profile - it finds them all anew, beside those the overrides give -, so that it replaces
  the outdated ones. The cost: until then a reference, or its coverage, may no longer be true, and
  nothing in the profile says so.
- **Drop both directions**: consistent with the reason of 35, but a profile scanned again has no
  references at all until `relate` runs.
- **Keep them, marked as outdated**: tells the report and the contract, but needs a field of the
  profile and a change of its format, which nobody needs yet.

## Done when

A table a scan counts anew keeps its references and reference candidates, but those of a column it
no longer has, with tests of both; the principle in `docs/ARCHITECTURE.md`, its description of
`scan`, `docs/PROFILE.md` and the module docs of `scan` say so.

## History

2026-11-12: Opened on the maintainer's request, who prefers references possibly outdated to none;
decided to keep both directions.

2026-11-12: Built: `Profile.updated` keeps of the table it replaces, beside what describe filled,
the references and reference candidates of the columns the table counted anew still has, and drops
of every table, the one counted anew included, those to a column it no longer has - a reference of
the table to itself as well. `_described` became `_filled`, as it fills in what the stages after
scan filled. The principle in `docs/ARCHITECTURE.md` lost its exception, and its description of
`scan`, `docs/PROFILE.md`, the README and the module docs of `scan` and `profile` say that what is
kept may be outdated until `relate` runs again.

2026-11-12: Decided with the maintainer: the references kept keep their order too, though the
columns may since be in another, as every stage changes only the values it fills; only what a scan
no longer finds - a table, a column - is dropped. The principle says so, and the attributes of the
references that their order is that of the columns as `relate` found them.
