# 50 — A probe of too many columns is refused

**Status:** done
**Type:** bug
**Priority:** high
**Area:** Relate
**Summary:** The stage relate puts every column indicated for ten keys into one query, without a limit, so that on a wide schema Starburst refuses the query for having too many stages and relate fails.

## The problem

On a schema of many columns, `relate` fails where Starburst refuses a query of its probes:

> too many stages (478, maximum is 150)

`_probed` of the module `references` limits the keys of a query to `PER_QUERY`, ten, but not the
columns probed in it: every column indicated for any of those keys is one, however many there are.
`Dialect.probed` reads each column by a branch of its own of a `UNION ALL`, as each takes its values
by a `LIMIT` of its own.

Measured by `EXPLAIN (TYPE DISTRIBUTED)` on the simulation environment, a statement of probes is
planned with one stage for each column and three more, whatever the number of keys: 4 stages for 1
column, 13 for 10, 43 for 40, the same for one key as for ten. The query refused held about 475
columns.

The coverage is not concerned: `covered` is planned with 12 stages for its ten lookups at most.

## Considerations

- **A limit of the columns of a query, beside that of the keys.** A column of a query is a stage of
  it, so that what is missing is a limit, not another statement. It costs more queries where there
  are many columns, each reading what it would have read anyway.
- **Reading the columns of a table together.** One read of each table for all its columns would need
  fewer stages, but each column takes its share of the rows and ends once it has taken its values,
  by a sampled read of its own: columns of one table in one read would hold a common share and
  limit. It changes what is probed in order to save queries that cost little.
- **Raising `query.max-stage-count` of the cluster.** It is not the tool's to set, and a query of
  hundreds of stages is what the setting is there to refuse.
- **`PER_QUERY` for the columns as well.** It is about what a query holds in memory; the columns of
  a probe hold a hundred values each. It would make ten times as many queries as are needed, for a
  reason that does not apply.

## The decision

The columns of a query of probes are limited by a constant of their own, `PROBES_PER_QUERY` of the
module `source`, beside `PER_QUERY`: 100, of 103 stages, which leaves room for a database that plans
somewhat otherwise or is set more narrowly than 150. `_probed` splits the columns of each batch of
keys by it; `Dialect.probed` stays as it is.

## Done when

- No statement of probes holds more than `PROBES_PER_QUERY` columns, and the references of more
  columns than that are found as those of fewer are.
- The documents on `relate` say so.

## History

- **2026-11-10** — Opened: `relate` failed on Starburst with too many stages (478, maximum is 150).
  Measured on the simulation environment, and the limit decided with the maintainer.
- **2026-11-10** — Done: `_probed` splits the columns of each batch of keys by `PROBES_PER_QUERY`.
  The measurement above holds only for tables with statistics. Tables just loaded, without them, are
  planned with two stages for each column and twelve more, for ten keys: 92 for 40 columns, 150 for
  69, refused for 70. The limit of 100 decided above would be refused there, so that it is 50
  instead: 53 stages with statistics, 112 without. The query refused may so have held about 233
  columns.
