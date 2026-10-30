# 13 — Projects and environments

**Status:** in progress
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
