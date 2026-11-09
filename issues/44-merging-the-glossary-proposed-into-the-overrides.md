# 44 — Merging the glossary proposed into the overrides

**Status:** open
**Type:** feature
**Priority:** medium
**Area:** Profile
**Summary:** What `describe` proposes of the glossary reaches the overrides only where a person copies it there by hand, concept by concept and into the right one of several files, so that the glossary of a project does not grow with what the tool found and a proposal a person agrees with stays a proposal.

## The problem

`describe` proposes concepts into the glossary of the profile of one environment. The overrides are
laid over it, and nothing of a profile is ever written back to them: the overrides are written by
hand alone. A person who agrees with a proposal has to find it in the profile, or the report, and
copy its word, its abbreviations and its description into a file of the overrides - the file the
concept is already given in, where it is, as a field given in two files is refused.

## Why it matters

The glossary is what the harmonized names are composed from, and a database has hundreds of
concepts. A proposal stands only until `describe --anew` drops it, and is of one environment alone,
while a concept given holds for all environments, is written in the terms given alone, and is not
asked of the language model again. Without a way of taking proposals over, the glossary given either
stays small or costs hours of copying, and there is no overview of where the overrides and the
results disagree.

## What is wanted

As the maintainer asked: a step of its own, working name `merge`, that takes what `scan` and
`describe` found into the project interactively, in particular the glossary of the overrides. It
runs on an environment of a project, as the stages do:

1.  It reads the concepts given, from all files of the overrides.
2.  It reads the concepts of the results.
3.  It compares them, concept by concept:

| What it finds | What it does |
|---|---|
| both entries of a concept are identical, in description and abbreviations | a short message, then the next |
| a concept the overrides do not have, or have no description of | asks whether to add it so: `Y` yes, `N` no, `M` manual, where the person enters the description |
| the abbreviations differ | asks the same; at `M` the person enters all abbreviations, separated by commas, in one line |

Where it writes follows from the several files of the overrides
([40](40-overrides-in-several-files.md)): a change of an existing entry is made in the file the
entry is defined in, and a new entry is added to the file `glossary.yml`.

What else of the results could be taken over - readings, descriptions of columns - is not part of
this issue; each would be an issue of its own, once somebody needs it.

## What the code already implies

- **Neither glossary at hand is what is to be compared.** The glossary of the profile holds
  proposals that the overrides have made void: `_laid_over` in `overrides` drops a concept proposed
  whose abbreviations a concept given has all taken, and takes those terms from the others, so that
  comparing with the profile as it is would offer `client: [cust]` beside a given
  `customer: [cust]`.
  The glossary laid over, on the other hand, has lost what is wanted of a concept given without a
  description: `replace(given[word], ...)` keeps the description given, that is none, and drops the
  proposed one. The comparison needs the rule of `_laid_over` and the proposed description, from
  one owner, not a second copy of the rule. Answers change it within a run: a concept added takes
  its terms from the proposals after it.
- **"The abbreviations differ" has a direction.** The language model is not asked of a term of a
  concept given, so that a concept proposed usually lacks the abbreviations given, and a comparison
  for equality would ask at nearly every such concept. What is new is only what `_laid_over` calls
  `left`: the abbreviations proposed that the concepts given do not have.
- **A concept may be spread over several files**, as the files are merged key by key: one file may
  give its abbreviations and another its description. "The file it is defined in" is therefore a
  matter of the field, not of the concept.
- **`Overrides.read` keeps no origin**: `Format.read_merged` merges the documents and hands on one
  value, so that which file gives what has to be found from the files.
- **The overrides are written by hand, with comments**, as `examples/crm/overrides.yml` shows;
  `Format.write` dumps by `safe_dump`, which would drop every comment.
- **Nothing of the tool is interactive yet**, and the frame of `commands` knows no input.

## What is to be decided

- **The name.** `merge` is already the word for what `Format.read_merged` does to the files of the
  overrides, and for what `PROJECT.md` describes of them; one word for two things is against
  *Concepts are named*. Either the word is kept apart by its context, or the step is called
  otherwise, `adopt` for one, which says that proposals are taken over. Recommended: `adopt`.
- **What `Y` means where abbreviations differ.**
  - *The proposed ones are added to those given.* Recommended: nothing given is lost, and it is what
    `_laid_over` does in every stage; a person who wants fewer answers `M`.
  - *The proposed ones replace those given* - would remove, at a plain `Y`, abbreviations the
    language model was never asked of.
- **Two descriptions that differ** are not in the table above. The language model words a concept
  anew in every run, so that asking would ask of nearly every concept with each run. Recommended:
  the description given stands, with the short message, and no question.
- **A proposal answered `N`** is still in the profile, and is asked of again at the next run.
  - *Asked again.* Simple, and needs no new concept; annoying where many are refused.
  - *Refusals are recorded*, in a form of their own beside the overrides - one more thing to keep,
    of which a person must know. Recommended: asked again, until it proves a burden.
- **The field that no file gives yet.** A change of a field is made in the file that gives the
  field. A field that no file gives - the description of a concept given without one - goes to the
  file that names the concept, the first of them in the order of `Project.overrides` where several
  do. Recommended as written.
- **Which `glossary.yml`.** Only `overrides.yml` and the files `*.yml` of `overrides/` are read, so
  that it has to be `overrides/glossary.yml`; made with the line `format:` of the current version
  where it does not exist.
- **How the files are written**, so that comments and the order of what a person wrote survive.
  - *A round trip by `ruamel.yaml`* - a new dependency beside PyYAML, or in place of it for this one
    use; the comments, the order and mostly the style are kept. Recommended.
  - *Editing the text of the files* - no dependency, but a second reader of YAML of our own, for
    flow style `{}` and block scalars.
  - *`Format.write`* - rejected, for the comments.
- **When it writes.** After each answer, as `describe` writes after each concept, so that a run
  interrupted loses nothing and the next one asks only what is left, or once at the end.
  Recommended: after each answer. Written whole by `files.write_whole`, as every document.
- **Where input ends.** A run whose input is no terminal, or ends, stops with an error and the
  answers given so far kept; nothing is answered by default.
- **What an answer may be.** Abbreviations are in lower case and a manual line is checked as the
  fields of the format are, an empty description or list being asked of again.
- **Who owns what.** The comparison belongs with the rule of `_laid_over` in `overrides`; writing a
  field into the file that gives it, with `documents`; asking the person, with a module of its own
  or `cli`. Whether this is a *stage* is to be decided as well: `docs/ARCHITECTURE.md` defines a
  stage as a step that works from what the stages before it left, and the stages hand on the profile
  alone, where this one writes the overrides and never the profile. The interface is put before the
  maintainer as the plan of the work.

## Done when

- A command run on an environment of a project goes through the concepts of its results and those
  of its overrides, and asks and writes as the table above and the decisions say.
- A change is written to the file that defines the entry, a new concept to the glossary file, and
  the comments and the order of every file written are kept; all this is tested with overrides of
  one file, of several, and with a concept spread over two.
- The overrides written are read by every stage without being refused, no field being given twice.
- A run answered by input other than a terminal behaves as decided, and is tested.
- `docs/PROJECT.md` has the command among what a person does with the overrides, with a recipe, and
  `docs/ARCHITECTURE.md` and the README name it.

## History

- **2026-11-09** — Opened, as the maintainer asked: an interactive step that compares the concepts
  of the overrides with those of the results, asks about each difference, and writes the answers to
  the files of the overrides.
