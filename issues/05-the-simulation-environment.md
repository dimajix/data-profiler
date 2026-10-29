# 05 — The simulation environment

**Status:** open
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
