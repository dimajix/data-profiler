# data-profiler

data-profiler is a command line tool for data engineers who have to understand an SQL database they
did not design - tables with dozens or hundreds of columns behind abbreviated names - and build an
understandable data model of it. Trino and Starburst are the first databases it reads; it writes
its SQL through a dialect, so that others can follow.

It works in three stages, each of which can be run again on its own:

- **scan** reads the selected tables, by a list or a regular expression, and finds for every column
  the range of its values, its nulls and the values that stand for none, such as empty texts or
  `9999-12-31`, whether it is an enumeration of few values, and what its values are - phone
  numbers, postal codes, card numbers, dates and more - by deterministic detectors, checked on a
  sample and, where they can, verified on the whole table; and which columns of a table are filled
  together, such as the street, the postal code and the city of a delivery address.
- **describe** splits the names of the tables and columns into their terms - mostly abbreviations,
  those written together as well - and reads each, a concept for every term, and asks a small
  language model, running locally in Ollama, for the concepts of the terms of none, and for a
  description of every column. Harmonized English names are composed from one glossary of the
  concepts of the whole schema - each a word, its abbreviations and a description -, so that the
  same concept reads the same in every table, whether written as its word or an abbreviation.
- **report** renders the result as HTML.

The result is a profile, a directory of YAML files - one for the schema and one for each table -
that holds no values of the columns found sensitive - personal or payment card data - and can be
shared; samples of the data stay in a local workspace. No value leaves the machine the tool runs
on.

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
- [Docker](https://www.docker.com/), for the simulation environment and the dev container.

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
  `docker compose --profile ollama up -d --wait`. Its models stay in a volume; the model of the
  example project is pulled once, by
  `curl http://localhost:11434/api/pull -d '{"model": "qwen3.5:2b"}'`.

It is filled with the tables of a profile, with generated rows that have the statistics of the
profile and, in the texts of a column with a match, the values of its semantic type, by

```bash
uv run simulation load simulation/profiles/crm
```

where `simulation/profiles/crm` is an example in the manner of a CRM. Only a profile of the
catalog `crm` is loaded; its schema is created where it does not exist, and its tables replace those
of the same names.

### Profiling a Database

The tool works on a project: a directory with its configuration `project.yml`, its variables in
`.env`, what is given by hand in `overrides.yml`, and the results of each of its environments - dev,
test, prod - in a directory named after the environment. `examples/crm/` is a project for the
simulation environment:

```yaml
format: 4
tables: .*
llm: qwen3.5:2b
environments:
  simulation:
    url: trino://localhost:8443/crm/sales
    user: profiler
    password: ${SIMULATION_PASSWORD}
```

- **`tables`** selects the tables of the whole project: a regular expression matched whole, or a
  list of their names.
- **`types`**, where there are any, gives the semantic types of the project, beside those of the
  tool, each under its name - lower case letters, digits and `-` -, by a pattern its values match
  whole, and its sensitivity, `none`, `personal` or `payment-card`:

  ```yaml
  types:
    account-number:
      pattern: "A[0-9]{10}"
      sensitivity: personal
  ```

  The pattern is read by Python and by the database alike, so it uses what both share: classes,
  repetitions, groups and alternatives, and no other escapes than of a character.
- **`llm`** names the language model of Ollama that `describe` asks, as Ollama names it; it is
  pulled into Ollama once. Where Ollama answers is a matter of the machine: the variable
  `OLLAMA_HOST`, as `http://host:port`, else `http://localhost:11434`. The tool reaches it past
  every proxy, as its prompts hold values of the database.
- **`environments`** names each environment by the URL of its schema,
  `trino://host:port/catalog/schema`, and the user and the password it is reached as. A value
  `${NAME}` is taken from the variable `NAME`; the password is given only so, never written out, so
  that `project.yml` can be committed and shared.
- **`.env`** holds the variables, and is never committed: the passwords, the users where they
  differ from one person to the next, and what reaches the database - `REQUESTS_CA_BUNDLE`, the
  certificate of a CA of one's own, and `NO_PROXY`, for a database no proxy reaches. A variable the
  process sets is not overridden by it - a `no_proxy` the shell sets, for one, has to name the
  database itself. For the example, copy
  `examples/crm/.env.example` to `examples/crm/.env`, and set the absolute path of the certificate
  of the simulation in it.
- **`overrides.yml`**, where there is one, gives by hand what a profile is to take as given:
  concepts of the glossary, each under its word with its abbreviations, its description and, where
  it is to be left out of the names, `omitted: true`; the reading of the name of a table or column,
  a concept for each of its terms, `reading: [airplus, contact_person, name]`; the harmonized name
  of a table or column, in snake_case, in place of the one composed from its reading, as where two
  columns would share one, `name: contact_person_id`; the description of a column, in place of the
  one proposed; the sensitivity of a column the detectors miss, such as the names of persons; and
  the values that stand for no value in a column, its sentinels, in place of those of the tool:
  `sentinels: ["", "00000"]`, or `sentinels: []` for none. `examples/crm/overrides.yml` shows them
  all; `scan` counts and marks the columns as they give, `describe` splits and reads the names by
  the concepts they give and asks the language model for nothing given, and `report` lays them over
  the profile.

With the simulation environment loaded, as above, the example is scanned by

```bash
uv run data-profiler scan simulation --project examples/crm
```

which writes the profile to `examples/crm/simulation/profile/` - `profile.yml` of the schema, and
a file of each table in `tables/` -, and the samples and enumerations of the tables to the
workspace `examples/crm/simulation/workspace/`, which keeps itself out of version control. The
profile is written after every table and updated, not replaced, by the next scan: the tables no
longer selected are dropped, and what `describe` filled is kept. A scan that failed or was
interrupted is resumed by the next one, which counts only the tables it did not; once a scan has
counted every table, the next one counts them all anew. A profile that cannot be read - of an older
format, for one - or of another schema is refused, never overwritten; it is removed by hand before
it is scanned anew. Without `--project`, the project is the current directory. The progress goes to
standard error; with `--debug` before the command, the log holds the statements sent and the values
of the database, and stays on the machine.

The names of the profile are split into their terms and read by

```bash
uv run data-profiler describe simulation --project examples/crm
```

without the database, by the concepts of the profile and of the overrides; the language model of the
project proposes a concept of each term of none, shown the samples of the workspace but of the
columns of a sensitivity, into the glossary of the profile, chooses the concept of each term of
several in a name, of which the reading of the name is made, and proposes a description of each
column. A concept proposed, a reading chosen or a description proposed wrongly is corrected in
`overrides.yml`, which comes first. It asks only for what the profile lacks, and writes the profile
after each concept and each table read or described, so that a run interrupted is resumed by the
next; `--anew` drops first what the language model filled, to describe the profile anew, with
another model, say. The profile is rendered as a report by

```bash
uv run data-profiler report simulation --project examples/crm
```

which lays the overrides of the project over it and writes `examples/crm/simulation/report.html`:
one file, which a browser shows and prints on its own, without the database. Its harmonized names
are composed from the readings, so that a profile not described has none but those the overrides
give.

### Running Tests

```bash
uv run pytest
```

Tests that need the simulation environment expect it to run, Ollama with the model of the example
project among it. The other checks, which the pre-commit hook runs as well, are listed in
[docs/CODING-GUIDELINES.md](docs/CODING-GUIDELINES.md#checks).

### The Dev Container

On a machine that reaches the real database - Windows with Docker Desktop, say -, the tool runs in
a dev container of Visual Studio Code, with Python, uv and the project made in it, and Ollama
beside it, which it reaches as `http://ollama:11434`. It needs Docker and the extension Dev
Containers of Visual Studio Code; for a clone in WSL also the extension WSL, and the integration of
Docker Desktop with that distribution of WSL.

1. Clone the repository. On Windows, a clone in the file system of WSL is mounted into the
   container much faster than one on `C:`. The container reaches only what lies in the clone, so
   the projects to profile go into its `projects/`, a repository of their own that this one
   ignores.
2. Put the certificates of the company into `.devcontainer/certs/`, each in PEM in a file ending
   in `.crt` - exported from the certificate manager of Windows as "Base-64 encoded X.509" -, the
   CA of the database among them: in the container, it is trusted from there, and a
   `REQUESTS_CA_BUNDLE` in the `.env` of a project is passed over, as the container sets it. A
   certificate added later needs *Rebuild Container*.
3. Where a proxy is needed, set `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` where Docker Compose
   runs: as variables of the user of Windows for a clone on `C:`, in the environment of WSL for a
   clone there. Visual Studio Code is to be started anew after they change. The container takes
   them over, and reaches Ollama without the proxy.
4. Open the folder in Visual Studio Code and choose *Reopen in Container*. The container runs
   `uv sync` once it is made, and enables the pre-commit hook.
5. Pull a model into Ollama once, from a terminal of the container, for instance
   `curl http://ollama:11434/api/pull -d '{"model": "qwen3.5:2b"}'`; models stay in a volume,
   which the simulation environment shares.

The simulation environment is not part of the container: the tests that need it fail in it and run
outside, the other checks and the tool inside.

### Working on the Repository

The pre-commit hook in `.githooks` keeps the issue overviews up to date and checks every commit
(see [docs/CODING-GUIDELINES.md](docs/CODING-GUIDELINES.md#checks)). Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

## License

data-profiler is licensed under the [Apache License, Version 2.0](LICENSE).
