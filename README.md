# data-profiler

data-profiler is a command line tool for data engineers who have to understand an SQL database they
did not design - tables with dozens or hundreds of columns behind abbreviated names - and build an
understandable data model of it. Trino and Starburst are the first databases it reads; it writes
its SQL through a dialect, so that others can follow.

It works in three stages, each of which can be run again on its own:

- **scan** reads the selected tables, by a list or a regular expression, and finds for every column
  the range of its values, its nulls, whether it is an enumeration of few values, and what its
  values are - phone numbers, postal codes, card numbers, dates and more - by deterministic
  detectors, checked on a sample and, where they can, verified on the whole table.
- **describe** asks a small language model, running locally in Ollama, for a harmonized English
  name and a description of every column. The names are composed from one glossary of the terms of
  the whole schema - mostly abbreviations -, so that the same term reads the same in every table.
- **report** renders the result as HTML.

The result is a profile, a YAML file that holds no values of the columns found sensitive - personal
or payment card data - and can be shared; samples of the data stay in a local workspace. No value
leaves the machine the tool runs on.

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

It is filled with the tables of a profile, with generated rows that have the statistics of the
profile and, in the texts of a column with a match, the values of its semantic type, by

```bash
uv run simulation load simulation/profiles/crm.yml
```

where `simulation/profiles/crm.yml` is an example in the manner of a CRM. Only a profile of the
catalog `crm` is loaded; its schema is created where it does not exist, and its tables replace those
of the same names.

### Profiling a Database

The tool works on a project: a directory with its configuration `project.yml`, its variables in
`.env`, what is given by hand in `overrides.yml`, and the results of each of its environments - dev,
test, prod - in a directory named after the environment. `examples/crm/` is a project for the
simulation environment:

```yaml
format: 1
tables: .*
environments:
  simulation:
    url: trino://profiler@localhost:8443/crm/sales
    password: ${SIMULATION_PASSWORD}
```

- **`tables`** selects the tables of the whole project: a regular expression matched whole, or a
  list of their names.
- **`environments`** names each environment by the URL of its schema,
  `trino://user@host:port/catalog/schema`, and the password of its user. A value `${NAME}` is taken
  from the variable `NAME`; the password is given only so, never written out, so that
  `project.yml` can be committed and shared.
- **`.env`** holds the variables, and is never committed: the passwords, and what reaches the
  database - `REQUESTS_CA_BUNDLE`, the certificate of a CA of one's own, and `NO_PROXY`, for a
  database no proxy reaches. A variable the process sets is not overridden by it - a `no_proxy` the
  shell sets, for one, has to name the database itself. For the example, copy
  `examples/crm/.env.example` to `examples/crm/.env`, and set the absolute path of the certificate
  of the simulation in it.
- **`overrides.yml`**, where there is one, gives by hand what a profile is to take as given: the
  word of a term, and the sensitivity of a column the detectors miss, such as the names of
  persons. `examples/crm/overrides.yml` shows both; `report` lays them over the profile, and so
  will `describe`, once it is made.

With the simulation environment loaded, as above, the example is scanned by

```bash
uv run data-profiler scan simulation --project examples/crm
```

which writes the profile to `examples/crm/simulation/profile.yml`, and the samples and enumerations
of the tables to the workspace `examples/crm/simulation/workspace/`, which keeps itself out of
version control. Without `--project`, the project is the current directory. The progress goes to
standard error; with `--debug` before the command, the log holds the statements sent and the
values of the database, and stays on the machine.

The profile is rendered as a report by

```bash
uv run data-profiler report simulation --project examples/crm
```

which lays the overrides of the project over it and writes `examples/crm/simulation/report.html`:
one file, which a browser shows and prints on its own, without the database.

### Running Tests

```bash
uv run pytest
```

Tests that need the simulation environment expect it to run. The other checks, which the
pre-commit hook runs as well, are listed in
[docs/CODING-GUIDELINES.md](docs/CODING-GUIDELINES.md#checks).

### Working on the Repository

The pre-commit hook in `.githooks` keeps the issue overviews up to date and checks every commit
(see [docs/CODING-GUIDELINES.md](docs/CODING-GUIDELINES.md#checks)). Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

## License

data-profiler is licensed under the [Apache License, Version 2.0](LICENSE).
