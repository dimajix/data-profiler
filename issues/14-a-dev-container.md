# 14 — A dev container

**Status:** in progress
**Type:** feature
**Priority:** high
**Area:** Tooling and process
**Summary:** The tool cannot be run on the machine that reaches the real database in a prepared environment: it has to be set up there by hand, on Windows, with its proxy, its certificates and a local language model.

## The problem

The trial of [04](04-can-a-small-model-name-columns.md) runs on the machine of the maintainer that
reaches the real database - Windows with Docker -, where the data has to stay. There the tool, uv,
Python 3.13 and a local language model in Ollama would each be set up by hand, beside the proxy and
the certificates of the company. The maintainer works there in Visual Studio Code.

## Why it matters

The trial of [04](04-can-a-small-model-name-columns.md), the largest risk of the first version,
waits for it; and every later run on the real database - `scan`, `describe`, `report` - needs the
same environment.

## What is to be decided

The plan first, put before the maintainer.

- **The container.** A dev container of Visual Studio Code, `.devcontainer/`, of an image with
  Python 3.13 and uv, which runs `uv sync` once it is made; the clone of the repository is mounted
  into it, its environment of Python kept out of the clone, apart from one made on Windows.
- **The language model.** Ollama beside the container, as a service of the same compose, so that
  the tool reaches it by its name; its models in a volume, kept when the container is made anew;
  a GPU where the machine has one.
- **The network.** The proxy of the company passed into the container from the environment of
  Windows; certificates of the company as a file the project names in its `.env`. Whether the
  simulation environment is reached from the container as well - its certificate is made for
  `localhost` - or the container is for the real database alone.
- **Windows.** Line endings are LF already (`.gitattributes`); a clone on the file system of WSL
  is much faster to mount than one on `C:`, which `README.md` says.
- **Tests of it.** A container cannot be built where the agents work, which cannot run Docker; it
  is tried by the maintainer.

## How

As decided with the maintainer:

- **For the real database and Ollama alone.** The simulation environment is not reached from the
  container, whose name of Trino would not be the `localhost` of its certificate; the tests that
  need it run outside.
- **No GPU:** the machine has an Intel CPU alone; Ollama runs on it.
- **Certificates** go into `.devcontainer/certs/`, named so as in other projects of the
  maintainer.

## Done when

- The plan is agreed with the maintainer.
- Visual Studio Code on Windows opens the repository in the container, and `uv run data-profiler`,
  the checks and the tests that need no simulation environment, and a call of Ollama run in it.
- `README.md` says how the container is opened, and what it needs on the machine.

## History

- **2026-10-30** — Opened as the maintainer asked for a dev container for the trial of
  [04](04-can-a-small-model-name-columns.md) on the real database.

- **2026-10-30** — The plan agreed with the maintainer, and made: `.devcontainer/` with a
  `Dockerfile` of the image of Python 3.13 of the dev containers and uv, the certificates of
  `certs/` added to its trust, which uv (`UV_SYSTEM_CERTS`) and requests (`REQUESTS_CA_BUNDLE`) use;
  a `compose.yml` of the container, the clone mounted into it, its environment of Python out of
  the clone, the proxy of the machine taken over and never used for Ollama, and Ollama beside it
  with its models in a volume; and `devcontainer.json`, which makes the environment and enables
  the hook. Not tried here, as the agents run no Docker: it is tried by the maintainer.
  After the review: the image of the container is of a fixed version, as every other image; Ollama
  trusts the certificates of `certs/` as well, to pull models through a proxy that inspects TLS,
  and shares its volume of models with the simulation environment; the proxy is taken over as the
  machine sets it, and left unset where it does not, so that one Docker gives the container is not
  overridden; git is told that the clone is safe by variables, not by a `.gitconfig`; the editor
  checks with ruff and mypy of `uv.lock`; `README.md` names the cases of WSL and of `C:`, and how
  certificates of Windows are exported.
  As the maintainer asked then, Ollama runs from its image for AMD GPUs, `0.40.13-rocm`, of 1.45 GB
  against 3.39 GB of the one with the libraries for NVIDIA, as Ollama falls back to the CPU with
  either; that image is for amd64 alone, so that the simulation environment keeps the other.
