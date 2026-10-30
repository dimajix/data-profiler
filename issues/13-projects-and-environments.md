# 13 — Projects and environments

**Status:** done
**Type:** feature
**Priority:** high
**Area:** Command line
**Epic:** [02](02-first-version-epic.md)
**Summary:** Nothing keeps the configuration of a database together with the results of profiling it, so every run is given the URL, the tables and the paths anew, and the same database in dev, test and prod cannot be profiled side by side.

## The problem

The command line planned in [07](07-the-stage-scan.md) takes the URL, the selection of tables, the
profile and the workspace as arguments, and the password from `.env`. A data engineer profiles one
database - the CRM - in several environments, dev, test and prod, each a schema of its own with a
URL and a password of its own, and wants their results apart. Nothing ties the configuration of the
database to its results, and nothing tells one environment from another.

## Why it matters

The profile of each environment is the work of a run of hours, and is compared, corrected and
shared; it has to be found again where it was made, under the name of its environment. The
configuration, written once, is what the team shares; the passwords must never be in it.

## How

As decided with the maintainer:

- **A project** is a directory: its configuration `project.yml`, its variables in `.env`, and a
  directory of results for each environment, `<environment>/profile.yml` and
  `<environment>/workspace/`.

  ```
  crm/
    project.yml       # committed: the tables, the environments
    .env              # not committed: passwords, URLs if they differ per person
    .env.example      # committed: which variables the project expects
    dev/
      profile.yml
      workspace/      # keeps itself out of version control
    prod/
      ...
  ```

- **`project.yml`** names the tables, for the whole project - a regular expression matched whole,
  or a list of names -, and the environments, each by its URL and its password. A value
  `${NAME}` is taken from the variable `NAME`: from the environment of the process, else from the
  `.env` of the project, which python-dotenv reads and which does not override what the process
  has. The password is given only as such a variable; a password written out is refused, so that
  the file can be committed and shared.

  ```yaml
  format: 1
  tables: cust.*|ord.*
  environments:
    simulation:
      url: trino://profiler@localhost:8443/crm/sales
      password: ${SIMULATION_PASSWORD}
    prod:
      url: ${CRM_PROD_URL}
      password: ${CRM_PROD_PASSWORD}
  ```

- **The command line** runs a stage on one environment of a project:
  `data-profiler [--debug] scan ENVIRONMENT [--project DIR]`, the project in the current directory
  if none is given.
- **The module `data_profiler.project`** reads a project as `data_profiler.profile` reads a
  profile - pydantic at the boundary, an exception class `ProjectError` of its own - and resolves an
  environment: its URL and password, the variables resolved, and the paths of its profile and
  workspace. A missing variable is named, with the environment and the file. The password never
  appears in a representation, a log or a message.
- **The name.** *Environment* is the word for the concept. The class
  `simulation.environment.Environment`, the connections to the simulated database, is renamed
  `Simulation` first, in a refactoring of its own; the simulation environment, in the documents,
  is one environment in the new sense.
- **An example project**, `examples/crm/`, with the environment `simulation`, for the tests and for
  `README.md`.
- **Settings per environment** beyond URL and password - a certificate of its own for prod - are
  not made before someone needs them: `REQUESTS_CA_BUNDLE` and `NO_PROXY` come from the `.env` of
  the project, for all its environments.

In steps, each reviewed and committed on its own:

1. The class of the simulation is renamed `Simulation`.
2. Reading and writing YAML in a format moves from `data_profiler.profile` into a module of its
   own, `data_profiler.documents`, a refactoring for the project to read its configuration the
   same way.
3. The module `data_profiler.project`, the example project, and the documents.
4. The command line, as step 4 of [07](07-the-stage-scan.md), which builds on the steps before,
   in two: first, a refactoring, what every command line of the project does around its work -
   the log configured, the program ended when the work fails - moves from `simulation.cli` into
   `data_profiler.commands.run`; then the command `scan` of the tool runs through it.

To be settled in their issues: overrides ([11](11-overrides.md)) and the glossary
([09](09-the-glossary.md)) likely belong to the project, the same for all its environments, while
the results of `describe` ([10](10-the-stage-describe.md)) and `report`
([12](12-the-stage-report.md)) are per environment.

## Done when

- `data_profiler.project` reads `project.yml` and resolves an environment, and refuses a password
  written out and a variable that is not set, naming it.
- The command line of [07](07-the-stage-scan.md) runs `scan` on an environment of a project,
  writing its profile and workspace into the directory of the environment.
- The example project scans the simulation environment.

## History

- **2026-10-30** — Opened from step 4 of [07](07-the-stage-scan.md), the command line, as the
  maintainer asked to think in projects and environments rather than in arguments. The interface of
  `data_profiler.project` is put before the maintainer before it is built; step 4 of
  [07](07-the-stage-scan.md) builds on it.

- **2026-10-30** — Step 1 done: the class `simulation.environment.Environment` is renamed
  `Simulation`, and the variables that held one with it, so that *Environment* is free for the
  environments of a project. The module keeps its name: it is the database of the simulation
  environment, which is one environment in the new sense.

- **2026-10-30** — Issue [07](07-the-stage-scan.md) is merged into `main` without its step 4, and
  this branch rebased onto it, so that the project builds on `data_profiler.files`. Step 2 done, a
  refactoring without a change of behaviour: reading and writing YAML in a format moves from
  `data_profiler.profile` into a module of its own, `data_profiler.documents`, for the project to
  read its configuration the same way; `Profile.read` and `Profile.write` translate its
  `DocumentError` into `ProfileError`. With it move the tests of what is refused in any document.
  Unknown fields are refused by `read_document` for every class it reads, nested ones included,
  rather than by a configuration that each class has to carry, so that the classes of the profile
  lose theirs. The field `format` is the document's own; a class a document holds has none. One
  message changes, for the maintainer's review: a file whose content is no mapping now "holds no
  fields", where it "holds no profile" before, since the module does not know what kind of
  document it reads.

- **2026-10-30** — Step 3 done: the module `data_profiler.project` reads the configuration of a
  project as a document, and resolves an environment by its name, its values `${NAME}` taken from
  the variables it is given when it is resolved, so that an environment is used without the
  variables of the others. It refuses, when the project is read, a password written out, a URL
  with a variable in it - a variable is taken only as the whole value -, an environment whose name
  is not lower case letters, digits, `-` and `_`, beginning with a letter or a digit - the name of
  its directory, the same on every system, and never taken for an option on the command line -,
  and tables that are no regular expression; a list of names becomes an alternation of the names
  as they are written. The example project `examples/crm/` profiles all tables of the simulation
  environment, and keeps its results out of version control; `.env` is kept out everywhere.
  Certificates and proxies now come from "the variables of the process", no longer "from the
  environment", in `data_profiler.source` and `docs/ARCHITECTURE.md`, since *Environment* is now
  the word for the environments of a project. `README.md` describes projects with the command
  line, in step 4.

- **2026-10-30** — Step 4 is made on this branch, as the maintainer agreed: the steps of
  [07](07-the-stage-scan.md) before it are in `main` already. Its first part done, a refactoring:
  the function `run` of a module of its own, `data_profiler.commands`, runs the work of a command
  with the log configured to standard error, and ends the program with the exit code 1 when the
  work fails, showing the message of the error classes it is given; `simulation.cli` runs its load
  through it, so that the log is configured in one place. The module is its own, as the maintainer
  decided, not a part of `data_profiler.cli`, which is the command line of the tool alone. The
  messages of a failure no longer name the load, but "the command", since `run` does not know what
  the work is. The tests of `simulation.cli` move to `test_simulation_cli.py`, so that those of
  `data_profiler.cli` will be in `test_cli.py`, as `docs/CODING-GUIDELINES.md` now says for
  modules of the same name.

- **2026-10-30** — Step 4 done, and with it the issue and [07](07-the-stage-scan.md): the module
  `data_profiler.cli` is the command line of the tool, `data-profiler [--debug] scan ENVIRONMENT
  [--project DIR]`, registered as a script of the project. It runs the stage through
  `data_profiler.commands.run`, showing the messages of the errors of the project, the source, the
  workspace and the profile. After the review, as the maintainer decided: `Project.read` completes
  the variables it is given - those of the process - by the `.env` of the project, overriding none,
  since `requests` reads the certificate and the proxies from there; the project owns its whole
  layout, a `.env` that cannot be read is an error of the project, and a variable that is not set
  is named with both places it could be set in. The tests of both command lines run them through
  one fixture, `command_line`, in a `conftest.py` of the root, which mypy tells apart from that of
  `tests/` by `explicit_package_bases`. The tool now
  names `trino` among its dependencies, which it imported without, reaching it only through the
  simulation in the environment of development, and `python-dotenv` for `.env`. `README.md` says
  how a project is made and scanned.
