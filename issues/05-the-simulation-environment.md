# 05 — The simulation environment

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Simulation
**Epic:** [02](02-first-version-epic.md)
**Summary:** There is no database to develop and test the tool against: the real Starburst is not reachable where the tool is developed.

## The problem

The tool reads Trino and Starburst, but where it is developed there is no access to either, and the
coding agents cannot start containers themselves. [01](01-initial-project-setup.md) decided on a
simulation environment in the repository, started by the maintainer before the tests that need it,
and reachable on `localhost`; and on a generator that fills it from a profile.

## Why it matters

Without it, nothing that talks to a database can be tested - neither
[06](06-source-and-dialect-for-trino.md) nor the stages after it -, and the tool cannot be tried out
before it meets the real database.

## How

In two steps, each reviewed and committed on its own:

1.  **The environment.** `docker-compose.yml`: Trino, its version fixed, with a catalog on
    PostgreSQL - which keeps its data across restarts and is loaded fast by `COPY` -, and Ollama
    under the compose profile `ollama`, with its models in the volume `ollama-models`, since an
    Ollama of its own may already run on the port. `README.md` names Docker as a prerequisite
    again and says how the environment is started.
2.  **The generator.** The project `simulation` creates the tables of a profile in PostgreSQL
    and fills them with values by `faker` (locale `de_DE`), loaded by `COPY`, and comes with an
    example profile in the manner of a CRM. Its first test lives in `simulation/tests/`, which
    is added to `testpaths` of pytest and `files` of mypy.

Things to settle on the way:

- **What the generator reads.** It may use only what a profile holds (decided in
  [01](01-initial-project-setup.md)): at first the columns, their types, the share of nulls and
  the values of enums; the semantic types, by which it chooses phone numbers, IBANs or names, come
  with [08](08-detection.md). Where it would need more than a profile holds, that is brought to
  the maintainer rather than added to the profile for its sake.
- **YAML in the repository.** The compose file is the first YAML file: `yml` and `yaml` are added
  to the wrapping of `scripts/wrapping.sh` with it.
- **Two `conftest.py`.** With `tests/` and `simulation/tests/` both checked by mypy, two modules
  named `conftest` collide; `explicit_package_bases`, or packages for the test directories, is
  decided once the second one appears.

## Done when

- `docker compose up` starts Trino and PostgreSQL; Trino answers on `localhost` and shows the
  catalog.
- The generator loads the example profile, and Trino returns its tables and rows.
- `README.md` says how the environment is started and how it is filled.

## History

- **2026-10-29** — Opened with the plan of the first version ([02](02-first-version-epic.md)).

- **2026-10-29** — Step 1 done: `docker-compose.yml` with PostgreSQL 18.6, Trino 484 and Ollama
  0.40.13, their versions fixed so that the environment does not change unnoticed. Trino is reached
  as Starburst is, by HTTPS with a password - the maintainer chose this over plain HTTP without one,
  so that the way the tool logs in is tried before it meets the real database. Its key and
  certificate are committed, made for the simulation alone: for `localhost` only and not a CA, which
  the strict verification of Python 3.13 and urllib3 accepts, as they allow a partial chain - a
  first certificate that was a CA was replaced after the review, since its key is public and
  trusting it would have trusted anything it signs. The password file holds bcrypt hashes of the
  form `$2y$`; how both are made is in `simulation/trino/config.properties`. `.gitattributes` keeps
  every text file LF on Windows too, where the Linux container could not read the password file
  otherwise. `scripts/wrapping.sh` covers `yml`, `yaml` and `properties`, and the comments of
  .gitattributes and .gitignore. Found on the way: where an HTTP proxy is set, `localhost` has to be
  in `NO_PROXY`, or requests to the simulation go to the proxy; that concerns the client of
  [06](06-source-and-dialect-for-trino.md).

- **2026-10-29** — Step 2 done, and with it the issue: `uv run simulation load PROFILE` creates the
  tables of a profile by Trino, from the types as Trino names them, and fills them by `COPY` in
  PostgreSQL, with rows that have the statistics of the profile - its rows, nulls, distinct values
  and the lengths of texts -, the same seed giving the same rows; `simulation/profiles/crm.yml` is
  the example, of six tables and about 97,000 rows, loaded in about a second. Weighed and decided:
  no `faker` yet, since what a column holds is known only from the semantic types of
  [08](08-detection.md) - until then texts are letters of the counted lengths. Trino names tables
  and columns in lower case, so a profile of Trino or Starburst does too. Found on the way: the
  import mode `importlib` of pytest took the directory `simulation/` for the package of the same
  name and hid it, so pytest imports test modules by name again, whose names are unique across both
  directories; two `conftest.py` work so, but mypy refuses them until `explicit_package_bases` is
  set, which waits for the first `conftest.py`. The command line of the simulation follows the rules
  of the tool's: it configures the log, with `--debug` for its tracebacks, and alone ends the
  program.

- **2026-10-29** — Changed while implementing and after the review, agreed by the maintainer:
  `SimulationError` lives in the package `simulation`, beside the description it shares, since the
  module `environment` imports `rows` from `data` and the agreed place would have been a circular
  import; `Environment` closes its connections as a context manager and counts the rows of a table
  by Trino, for the command line and the test; `--debug` shows the tracebacks the command line logs.
  A failure of Trino or PostgreSQL is told by the system, its endpoint and what was done, where the
  client is called; what the client said - a failed `COPY` names the value it refused - stays in the
  cause, logged at debug. The principles that the database is only read and that the dialect writes
  all SQL are the tool's; the simulation writes into its own environment.
