# The image of the dev container: Python 3.13 and uv, and the certificates of the company, which
# `certs/` holds on the machine, trusted by the system, so that uv and the tool reach through a
# proxy that inspects TLS. Its versions are fixed, so that it does not change unnoticed.
FROM mcr.microsoft.com/devcontainers/python:3.3.2-3.13-trixie

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /usr/local/bin/

# Only the files ending in .crt are taken; the folder may hold none.
COPY certs/ /usr/local/share/ca-certificates/company/
RUN update-ca-certificates
