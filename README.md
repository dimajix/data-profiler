# data-profiler

data-profiler is a command line tool for data engineers who have to understand an SQL database they
did not design - tables with dozens or hundreds of columns behind abbreviated names - and build an
understandable data model of it. Trino and Starburst are the first databases it reads; it writes
its SQL through a dialect, so that others can follow.

It works in three stages, each of which can be run again on its own:

- **scan** reads the selected tables, by a list or a regular expression, and finds for every
  column the range of its values, its nulls, whether it is an enum of few values, and what its
  values are - phone numbers, postal codes, card numbers, dates and more - by deterministic
  detectors, checked on a sample and, where they can, verified on the whole table.
- **describe** asks a small language model, running locally in Ollama, for a harmonized English
  name and a description of every column. The names are composed from one glossary of the terms of
  the whole schema - mostly abbreviations -, so that the same term reads the same in every table.
- **report** renders the result as HTML.

The result is a profile, a YAML file that holds no sensitive values and can be shared; samples of
the data stay in a local workspace. No value leaves the machine the tool runs on.

The project is at its beginning: the stages above are what it is being built for.

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: The overall picture - the parts of the project,
  how they work together, and the principles of the design -, with the detailed documents in
  [docs/](docs/).
- **[AGENTS.md](AGENTS.md)**: How we work together - for coding agents and contributors alike.
- **[issues/INDEX.md](issues/INDEX.md)**: Every issue, one line each, by area;
  [issues/OPEN.md](issues/OPEN.md) those still open. The reasoning is in
  `issues/<number>-<slug>.md`, how issues are kept in [issues/README.md](issues/README.md).

## Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/), which installs Python 3.13 and every dependency itself. Where
  uv does not download Python on its own, install it once with `uv python install 3.13`.
- [Docker](https://www.docker.com/), for the simulation environment.

The commands below are the same on Linux, macOS and Windows.

### Building the Project

In a clone of the repository:

```bash
uv sync
```

It creates the environment `.venv` with the tool and the test data generator, as `uv.lock` fixes
their dependencies.

### The Simulation Environment

The simulation environment stands in for the real database in the tests and wherever the tool is
tried out without access to it: a Trino that is reached as Starburst is, by HTTPS with a password,
on a PostgreSQL that holds the test data. It is started by

```bash
docker compose up -d --wait
```

and stopped by `docker compose down`; its data stays in a volume until
`docker compose down --volumes`.

- **Trino** answers on `https://localhost:8443`, with the catalog `crm`, to the user `profiler` with
  the password `profiler`. Its certificate, `simulation/trino/tls/trino.crt`, is made for the
  simulation alone, as its key beside it.
- **PostgreSQL** answers on `localhost:5432`: database, user and password are `crm`.
- **Ollama** is started with the profile `ollama`, on a machine on which none runs already:
  `docker compose --profile ollama up -d --wait`. Its models stay in a volume.

### Running Tests

```bash
uv run pytest
```

The other checks, which the pre-commit hook runs as well, are listed in
[docs/CODING-GUIDELINES.md](docs/CODING-GUIDELINES.md#checks).

### Working on the Repository

The pre-commit hook in `.githooks` keeps the issue overviews up to date and checks every commit
(see [docs/CODING-GUIDELINES.md](docs/CODING-GUIDELINES.md#checks)). Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

## License

data-profiler is licensed under the [Apache License, Version 2.0](LICENSE).
