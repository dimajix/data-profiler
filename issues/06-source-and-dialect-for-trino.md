# 06 — Source and dialect for Trino

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Scan
**Epic:** [02](02-first-version-epic.md)
**Summary:** The tool cannot reach a database: nothing connects to Trino, lists its tables or sends it a query.

## The problem

`docs/ARCHITECTURE.md` gives the database two concepts: the `Source`, which connects and runs
queries, and the `Dialect`, which writes every SQL statement the tool sends - so that another
database is a new dialect, not a change across the code. Neither exists, nor their implementations
for Trino.

## Why it matters

Every query of [07](07-the-stage-scan.md) and [08](08-detection.md) goes through them. Their
interfaces decide how far the tool stays open to other databases, which
[01](01-initial-project-setup.md) asked for - and how far it does so without an abstraction no
second database uses yet.

## What is to be decided

The interfaces first, put before the maintainer: `Source` and `Dialect` as abstract classes, their
methods with signatures and a one-line doc comment each, and `SourceError`.

- **What the source offers.** Listing the tables of a catalog and schema, selected by a list of
  names or a regular expression; listing the columns of a table with their types; running a query
  and returning its rows. Only what [07](07-the-stage-scan.md) needs first.
- **How SQL is written.** Text written per dialect, or statements built with `sqlglot` and
  rendered in the dialect. Recommendation: `sqlglot`, which knows Trino's functions
  (`approx_distinct`, `regexp_like`, `TABLESAMPLE`) and renders them for other databases, so that
  a second dialect is mostly a name.
- **The connection.** By URL, the password from `.env`, never in the URL (`python-dotenv`; `.env`
  is ignored by git, `.env.example` is committed). Reading `.env` belongs to `cli`; the source
  takes what it needs when it is made.
- **Errors.** A failure of Trino becomes a `SourceError` that names what failed - the table, the
  step - and keeps its cause; the message of Trino, which may hold a value of the database,
  reaches the log at `debug` alone (`docs/CODING-GUIDELINES.md`, "Logging").

## Done when

- The interfaces are agreed with the maintainer.
- Against the simulation environment ([05](05-the-simulation-environment.md)), the source lists
  the tables selected by a list and by a regular expression, their columns and types, and runs a
  query; a wrong password, an unknown table and a failing query each end in a `SourceError` naming
  what failed.
- `docs/ARCHITECTURE.md` says what holds of the source and the dialect.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-29** — Interface agreed with the maintainer and implemented in `data_profiler.source`.
  `Source` and `Dialect` are abstract classes already, since the maintainer asked to keep other
  databases open; `Source` lists tables and columns through its dialect and `query`, so that a new
  database brings only its connection and its SQL. `connect(url, password)` makes the source of a
  URL `trino://user@host:port/catalog/schema`; Trino is always reached by HTTPS, as a password needs
  it. Certificates and proxies come from the environment, as `requests` reads them
  (`REQUESTS_CA_BUNDLE`, `NO_PROXY`), which a probe confirmed. Tables are selected by a regular
  expression matching whole names; a list of names becomes one at the command line. Weighed:
  `sqlglot`, recommended above, was dropped - a probe showed that it quotes well but does not
  translate Trino's functions for another database, `approx_distinct` staying as it is for
  PostgreSQL, so a second dialect needs code of its own anyway; the SQL is written by hand, with
  quoted identifiers and literals. A deviation from the interface agreed: `query` takes the step its
  statement is for, so that a failure names it. A refused login is told apart by the status in the
  text of the client's error, as the client has no class for it.

- **2026-10-29** — After the review: a URL that holds a password, a query or a fragment is refused -
  the password is given apart from it -, and no message repeats the URL, which may hold one.
  `connect` makes the connection and the source takes it, as the guidelines have services held. A
  statement runs in the schema of its source, which `query` now says, as every database to come has
  to keep it.

- **2026-10-29** — Done. The maintainer confirmed the deviation: `query` takes the step its
  statement is for. Reported around the change, left as they are: the quoting of identifiers is
  written twice, here and in `simulation.environment`, which writes SQL of its own the tool does not
  offer; that module still writes `dbapi.Connection` by its path; and the path of the test
  certificate stands in `tests/test_source.py` and in `simulation.environment`.
