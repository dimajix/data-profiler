# 17 — The user apart from the URL

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Command line
**Summary:** The user of an environment is part of its URL, so that it cannot be taken from a variable while the host, the catalog and the schema stay in the configuration the team shares.

## The problem

An environment of a project ([13](13-projects-and-environments.md)) is given by its URL,
`trino://user@host:port/catalog/schema`, and its password, which is always a variable. The user
the database is reached as may differ from one member of a team to the next, as the password does,
and belongs with it in the `.env` of the project, not in `project.yml`. A variable is taken only
as the whole value, so the user can come from a variable only with the whole URL, and the host, the
catalog and the schema then leave the configuration that is committed and shared.

## Why it matters

The configuration says which database a project profiles; written in `.env` alone, it is kept by
each member apart, and differs without anybody noticing. The users of Starburst are often email
addresses or names with a domain, `DOMAIN\name`, which a URL can hold only encoded.

## What is to be decided

1. **A field `user` beside `password`, the URL without a user.** The credentials are given apart
   from where the database is, both alike, as `source.connect` already takes the password apart
   from the URL. The user is a value or a variable, as the URL is; the rule that a variable is
   taken only as the whole value stays. A user needs no encoding. It costs a new format of
   `project.yml`, and a URL that holds a user is refused, so that there is one way to give it.
2. **Variables in values, `trino://${CRM_USER}@host/crm/sales`.** The format stays, but the
   mechanism grows without another user: how a literal `${` is written, and the user would have to
   be encoded for the URL, which a substitution of text does not know - `kaya@dimajix.de` would
   change the URL silently.

## How

As decided with the maintainer: option 1.

- `project.yml`, format 3, gives each environment its `url`, `trino://host:port/catalog/schema`,
  its `user`, a value or `${NAME}`, and its `password`, `${NAME}` alone.
- `Environment.user` resolves the user as `url` and `password` are resolved.
- `source.connect(url, user, password)` refuses a URL that holds a user, as it refuses one that
  holds a password.
- A configuration of format 2 is refused, as any other format is; it is changed by hand.

## Done when

- An environment gives its user apart from its URL, as a value or a variable, and a variable of it
  that is not set is named.
- A URL with a user is refused.
- The example project and `README.md` give the user so.

## History

- **2026-11-02** — Opened, as the maintainer asked for the user of an environment to come from a
  variable, as its password does.
