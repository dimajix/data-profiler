# Coding Guidelines

The general rules for code in this project: style, structure, error handling, logging and tests.
Rules that belong to one subject live with the document on it. [ARCHITECTURE.md](ARCHITECTURE.md)
gives the overall picture, the principles of design are in
[AGENTS.md](../AGENTS.md#design-principles).

> **TODO (issue 01):** These rules are written for any language. Name the language here, fill in the
> [checks](#checks), and give each rule below that depends on the language its form in it - the
> error types, the logging library, how visibility is narrowed, where tests live -, with an example
> from the code once there is one. Rules that do not apply are deleted, not kept as dead letters.

## Rules for every change

The rules most often missed, each with the section that gives its reasons. Every change is checked
against this list, rule by rule, before it is reported (the self-review of
[AGENTS.md](../AGENTS.md#workflow)).

*   Import what you use at the top of the module and write it by its name, not by its path - also
    for a single use and in a test ([Imports](#imports)).
*   Every module begins with its description, whose first sentence names its responsibility
    ([Comments and documentation](#comments-and-documentation)).
*   Errors are handled or passed on, never ignored, and expected failures never end the program
    ([Error handling](#error-handling)).
*   An interface between parts answers an error type of its own, not a generic one
    ([Types of errors](#types-of-errors)).
*   Error messages name what failed and never contain secret values or file paths
    ([Messages name what failed](#messages-name-what-failed)).
*   Log through the project's logging library, never by printing; message content only at the
    most detailed level, credentials never ([Logging](#logging)).
*   A type takes the services it uses when it is made and keeps them; it does not fetch them at
    every use ([Services are held, not fetched](#services-are-held-not-fetched)).
*   Comments and Markdown documents wrap prose at 100 characters, and no line of it starts with a
    dash; `scripts/wrapping.sh` finds the lines of a change that break either
    ([Comments and documentation](#comments-and-documentation)).
*   A change comes with its tests, which use what the code offers its callers
    ([Testing](#testing)).
*   Every [check](#checks) passes: the tests, the formatter, the linter and the wrapping.

## Checks

The rules that a tool can check are checked by one; no rule a tool checks is checked by hand. Every
check passes before a change is reported ([AGENTS.md](../AGENTS.md#workflow)), and the pre-commit
hook in `.githooks` runs them on every commit, once a clone has it enabled
(`git config core.hooksPath .githooks`); `git commit --no-verify` skips them.

| Check | Command | In the pre-commit hook |
|---|---|---|
| The tests | TODO (issue 01) | no - they are run before every report |
| The layout of the code | TODO (issue 01) | yes, when code is part of the commit |
| The linter | TODO (issue 01) | yes, when code or its configuration is part of the commit |
| The wrapping of prose | `scripts/wrapping.sh` | yes, on the files the commit adds or changes |
| The issue overviews | `issues/generate.sh --check` | regenerated, when an issue is part of the commit |

> **TODO (issue 01):** The commands of the language, for example `cargo test`,
> `cargo fmt --all --check` and `cargo clippy --workspace --all-targets -- -D warnings` for Rust;
> `pytest`, `ruff format --check` and `ruff check` for Python; `go test ./...`, `gofmt -l .` and
> `go vet ./...` for Go. Add the formatter and the linter to `.githooks/pre-commit`.

*   **Code is laid out by the formatter**, with the settings of its configuration file, and never
    by hand. Where the formatter leaves something as it is written, its layout is the author's,
    within 100 characters as the formatter would lay it out.
*   **The linter stays silent.** Where a lint is wrong for a case, it is silenced on that item
    alone, with the reason, and in the form that is noticed once the lint no longer fires where the
    language offers one (`#[expect(…, reason = "…")]` in Rust).
*   **Rules a lint checks.** The configuration of the linter turns on the lints that check rules of
    this document, and the rule names its lint. A rule missed twice gets a lint, a test or a check
    of the hook ([AGENTS.md](../AGENTS.md#corrections-become-rules)).
*   **Long functions** are split, not silenced: a function longer than a screen does more than one
    thing.

## Comments and documentation

*   **Doc comments** document the public interface - types, functions, methods: what it does, its
    parameters, its return value and its errors.
*   **Internal comments** explain *why* something is done where the code does not show it, not
    what it does.
*   **Module docs:** every module begins with its description, and its first sentence names the
    module's responsibility - one sentence, without an "and also" (the test of
    [one owner per concern](../AGENTS.md#design-principles)). What follows describes the module in
    detail. A change after which that sentence no longer holds is a
    [finding](../AGENTS.md#findings); a module without such a sentence gets it when its content
    is changed anyway. A mechanical change across many modules - a lint's fix, a rename - does not
    count, so that it stays one change of its own.
*   **Consistency:** mirror the comment frequency and style of the module you are editing.
*   **Comments wrap at 100 characters**, as the Markdown documents do. Older comments are rewrapped
    when they are changed anyway, not on their own.
*   **Markdown documents** (`docs/`, `issues/`, `AGENTS.md`, `.claude/agents/`) wrap prose at 100
    characters. Headings, table rows, code blocks and links that would not fit stay on one line;
    field lines such as `**Status:**` keep a line of their own.
*   **No line of prose starts with a dash**, in comments as in Markdown documents. To a renderer of
    Markdown and of doc comments, a line that begins with `- ` is a list item, and the sentence it
    goes on with breaks apart; in a plain comment the reader takes it for one - also inside a list
    item. Wrap so that a dash ends the line before it instead. A list is told apart by the line
    before it: it follows a blank line, a heading, or a line that ends in `.`, `:`, `?`, `!` or a
    title in bold (`**…**`); a further item stands where the item before has its marker, not where
    its prose begins.
*   **Wrapping is checked by `scripts/wrapping.sh`**, in the files these rules cover: the Markdown
    documents above, and the comments of the source files whose languages it knows - lines that
    begin with a comment marker; a comment after code, and a docstring, are not checked. It counts
    lengths in characters, not bytes, by the exceptions above; a link counts as one word, not broken
    even in its text. It finds a line beginning with a dash where the prose of the line before
    begins - after its marker, in a list item -, if that line belongs to the same comment, is no
    heading or table row, and ends in none of the marks above. Without arguments it checks the lines
    a change adds or changes, against `HEAD`, and new files whole; given files, it checks those of
    them the rules cover, whole. The pre-commit hook gives it the files a commit adds or changes.
    Neither is checked by hand or with another tool: other tools count bytes or know no exceptions.

### What goes where

What is known about the code has three places, each kept by whoever changes what it describes:

*   **The documents in `docs/`** explain what the code does not show by itself: the concepts and
    who owns them; the principles and rules - invariants, orders, who checks what, what is never
    done and why; and how the parts fit together. A type or method is named where a reader needs
    the name to find the code - the name, not what it does in detail. A document says what holds,
    not how it came to be, and is read before every piece of work on its subject, so every line of
    it costs every reader.
*   **Doc comments and module docs** hold what one type, function or module does in detail: its
    variants and fields, its steps and their order, its errors, its constants. They are changed and
    reviewed with the code they describe.
*   **Issues** hold how something came to be: the options weighed and why one was chosen. A
    document links an issue only where a rule would otherwise look wrong or arbitrary and the issue
    says why - not to record which issue added what.

A change updates the document on its subject where it changes a concept, a rule or how the parts
fit together, and only the doc comments where it changes how something is done. A rule that only a
document states is moved, not dropped, when the document is shortened.

## Code structure

### Imports

A type, function or module used by name is imported at the top of the module and written by its
name, not by its path - also when adding the import means touching the import block for a single
use. A function may be called by its module where the module says where it comes from
(`time.sleep`, `fmt.Println`); two things of one name in one module are told apart by their modules,
or one is renamed on import.

### Small return values

A function that returns two values, called from a few places close to it - inside its module or
package, not a public interface - returns a tuple or several values, not a type made for it. A type
that only bundles a return value is one more name to read and keep. A type is worth it once the
value has a meaning of its own: it gets methods, travels further than its caller, is stored or
serialized, has more than two parts, or its parts have the same type and could be swapped
unnoticed.

### States are types

Fields that make sense only in certain combinations - two booleans of which only three combinations
occur, an optional field that is set exactly when another field has a certain value - become one
type whose variants hold what belongs to them: an enum, a sum type, a class per state. A state that
cannot be represented needs no check at its callers. The same holds for parameters: a boolean that
switches a function between two behaviours becomes two functions, or an enum that names the
behaviours.

### Services are held, not fetched

A type takes the services it works with - stores, clients, the configuration it reads - when it is
made, and keeps them as fields:

*   **Constructor injection.** The constructor takes the services; none is fetched again at every
    use, and none sits in a global, which would hide the dependency and tie every test to one
    instance.
*   **What it holds says what it needs.** A type holds the services it uses, not an object that
    reaches all of them. Several services that go together travel as a small context holding
    exactly those, never as one that holds everything again.
*   **No threading next to the owner.** A service is not passed into a function beside the object
    that already holds it; the function becomes a method of that object, or takes the object.

## Error handling

Errors carry what failed, and only what may be shown goes to users.

### Types of errors

*   An interface between parts - a trait, an abstract class, an interface type - answers an error
    type of its own: who implements it is not fixed, and its caller has to tell its errors apart.
    The type is the contract: what the caller can distinguish - what may be shown, a refusal, a
    failure of a backend.
*   A generic error type, or one that wraps any error, is used only where errors are gathered and
    passed on - at the top of a program or of a task, which logs them -, not at the boundary to
    implementations of others.
*   An expected failure never ends the program and is never silently dropped: it is passed on or
    handled. Ending the program is for broken invariants alone.

### Messages name what failed

*   An error caused by configuration names the setting and where it is set.
*   An error caused by a remote system names the endpoint, without credentials, query or fragment,
    and the chain of its causes.
*   Messages never contain secret values or file paths, because they may be shown to users.

### What users see

What users may see of an error is decided by whoever defines the error type, in one place each, not
by each caller. Anything else stays in the log.

### Rolling back

An operation that stored something and then fails part of the way is rolled back: what it stored
is set back to how it was before, and its caller gets the error. What cannot be set back is logged.

## Logging

### Setup

*   Every part logs through one logging library; nothing prints to standard output or standard
    error to log.
*   Libraries never configure where logs go; the program does, in one place.

### Levels

*   **error** only for failures that abort an operation.
*   **warn** for degraded but continuing operation.
*   **info** for lifecycle transitions: something starting or stopping, created or deleted.
*   **debug** for per-event detail. Anything that happens once per request or per store operation is
    debug at most; anything more frequent is trace.

### Content

*   The content of messages, documents and requests only at the most detailed level.
*   At debug and above, log ids, kinds and sizes.
*   Credentials, tokens and cookies are never logged, at any level.
*   Ids that tie records together belong in the context of a record - a span, a structured field
    -, not repeated in every message.

## Testing

A test uses what the code offers its callers. One that needs an internal - a field or method made
visible for it, beyond what a module offers for tests - says that a cut is wrong: it is a
[finding](../AGENTS.md#findings), and the visibility is not widened for it.

*   **Shared fixtures:** what the tests of several modules use lives in one place, offered by the
    module whose things it builds, and named apart from its own interface. A test builds what it
    needs as the code does, from defaults, and writes only what it differs in.
*   **Naming:** a test is named after what it shows, as a sentence:
    `a_document_saved_twice_keeps_both_versions`.
*   **Assertions** say what was expected, in their message where the assertion alone does not.
