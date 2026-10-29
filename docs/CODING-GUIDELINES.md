# Coding Guidelines

The general rules for code in this project: style, structure, error handling, logging and tests.
Rules that belong to one subject live with the document on it. [ARCHITECTURE.md](ARCHITECTURE.md)
gives the overall picture, the principles of design are in
[AGENTS.md](../AGENTS.md#design-principles).

The project is written in Python 3.13, its packages and tools managed by uv. Its language is
English: code, comments, documents, issues and commit messages are written in English, whatever
language the conversation about them is held in.

## Rules for every change

The rules most often missed, each with the section that gives its reasons. Every change is checked
against this list, rule by rule, before it is reported (the self-review of
[AGENTS.md](../AGENTS.md#workflow)).

*   Import what you use at the top of the module, absolutely, and write it by its name, not by its
    path - also for a single use and in a test ([Imports](#imports)).
*   Every module begins with its description, whose first sentence names its responsibility
    ([Comments and documentation](#comments-and-documentation)).
*   Errors are handled or passed on, never ignored, and expected failures never end the program
    ([Error handling](#error-handling)).
*   An interface between parts answers an exception class of its own, not a generic one
    ([Types of errors](#types-of-errors)).
*   Error messages name what failed and never contain secret values or values of the database
    ([Messages name what failed](#messages-name-what-failed)).
*   Log through `logging`, never by printing; values of the database only at `debug`,
    credentials never ([Logging](#logging)).
*   A class takes the services it uses when it is made and keeps them; it does not fetch them at
    every use ([Services are held, not fetched](#services-are-held-not-fetched)).
*   Comments and Markdown documents wrap prose at 100 characters, and no line of it starts with a
    dash; `scripts/wrapping.sh` finds the lines of a change that break either
    ([Comments and documentation](#comments-and-documentation)).
*   A change comes with its tests, which use what the code offers its callers
    ([Testing](#testing)).
*   Every [check](#checks) passes: the tests, the formatter, the linter, the type checker and the
    wrapping.

## Checks

The rules that a tool can check are checked by one; no rule a tool checks is checked by hand. Every
check passes before a change is reported ([AGENTS.md](../AGENTS.md#workflow)), and the pre-commit
hook in `.githooks` runs them on every commit, once a clone has it enabled
(`git config core.hooksPath .githooks`); `git commit --no-verify` skips them.

| Check | Command | In the pre-commit hook |
|---|---|---|
| The tests | `uv run pytest` | no - they are run before every report |
| The layout of the code | `uv run ruff format --check` | yes, when code or its configuration is part of the commit |
| The linter | `uv run ruff check` | yes, when code or its configuration is part of the commit |
| The types | `uv run mypy` | yes, when code or its configuration is part of the commit |
| The wrapping of prose | `scripts/wrapping.sh` | yes, on the files the commit adds or changes |
| The issue overviews | `issues/generate.sh --check` | regenerated, when an issue is part of the commit |

The tools and their settings are in `pyproject.toml`, their versions in `uv.lock`. The hook runs
them by `uv run --locked`, which also refuses a `uv.lock` that no longer fits the `pyproject.toml`
files.

*   **Code is laid out by the formatter**, with the settings of its configuration file, and never
    by hand. Where the formatter leaves something as it is written, its layout is the author's,
    within 100 characters as the formatter would lay it out.
*   **The linter stays silent.** Where a lint is wrong for a case, it is silenced on that item
    alone, with the reason after it: `# noqa: <code>  # <reason>` for ruff,
    `# type: ignore[<code>]  # <reason>` for mypy. Both report a silencing without its code
    (`PGH004`, `ignore-without-code`) and one that is no longer needed (`RUF100`, mypy's strict
    mode).
*   **Types are checked strictly.** `mypy` runs in its strict mode: every function is annotated,
    no untyped function is called, and no function returns `Any` where it declares a type.
*   **Rules a lint checks.** The configuration of the linter turns on the lints that check rules of
    this document, and the rule names its lint. A rule missed twice gets a lint, a test or a check
    of the hook ([AGENTS.md](../AGENTS.md#corrections-become-rules)).
*   **Long functions** are split, not silenced: a function longer than a screen, or one of many
    branches, does more than one thing. Ruff reports them (`PLR0915`, `C901`).

## Comments and documentation

*   **Doc comments**, docstrings in Python, document the public interface - classes, functions,
    methods: what it does, its parameters, its return value and its errors, in the Google convention
    with the sections `Args:`, `Returns:` and `Raises:`. Ruff checks that they are there and their
    form (`D`).
*   **Internal comments** explain *why* something is done where the code does not show it, not
    what it does.
*   **Module docs:** every module begins with its description, and its first sentence names the
    module's responsibility - one sentence, without an "and also" (the test of
    [one owner per concern](../AGENTS.md#design-principles)). What follows describes the module in
    detail. A change after which that sentence no longer holds is a
    [finding](../AGENTS.md#findings). Ruff reports a module without a description (`D100`,
    `D104`), and `tests/test_module_docs.py` one whose first paragraph is more than one sentence;
    a full stop followed by a space ends a sentence, so the first sentence writes no abbreviation
    with one.
*   **Consistency:** mirror the comment frequency and style of the module you are editing.
*   **Comments wrap at 100 characters**, as the Markdown documents do. Older comments are rewrapped
    when they are changed anyway, not on their own.
*   **Markdown documents** (`docs/`, `issues/`, `AGENTS.md`, `README.md`, `.claude/agents/`) wrap
    prose at 100 characters. Headings, table rows, code blocks and links that would not fit stay on
    one line; field lines such as `**Status:**` keep a line of their own.
*   **No line of prose starts with a dash**, in comments as in Markdown documents. To a renderer of
    Markdown and of doc comments, a line that begins with `- ` is a list item, and the sentence it
    goes on with breaks apart; in a plain comment the reader takes it for one - also inside a list
    item. Wrap so that a dash ends the line before it instead. A list is told apart by the line
    before it: it follows a blank line, a heading, or a line that ends in `.`, `:`, `?`, `!` or a
    title in bold (`**…**`); a further item stands where the item before has its marker, not where
    its prose begins.
*   **Wrapping is checked by `scripts/wrapping.sh`**, in the files these rules cover: the Markdown
    documents above, and the comments of the source files whose languages it knows - lines that
    begin with a comment marker, and the lines of a docstring; a comment after code is not checked.
    It counts lengths in characters, not bytes, by the exceptions above; a link counts as one word,
    not broken even in its text. It finds a line beginning with a dash where the prose of the line
    before begins, or further in - after its marker, in a list item -, if that line belongs to the
    same comment, is no heading or table row, and ends in none of the marks above. Without arguments
    it checks the lines a change adds or changes, against `HEAD`, and new files whole; given files,
    it checks those of them the rules cover, whole. The pre-commit hook gives it the files a commit
    adds or changes. Neither is checked by hand or with another tool: other tools count bytes or
    know no exceptions.

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
name, not by its path - `from data_profiler.profile import Profile`, then `Profile` -, also when
adding the import means touching the import block for a single use. A function of the standard
library or of `pytest` may be called by its module, which says where it comes from (`json.loads`,
`pytest.raises`); two things of one name in one module are told apart by their modules, or one is
renamed on import. Imports are absolute, never relative to the module (`from .profile import …`).
Ruff checks where imports stand (`PLC0415`), their order (`I`) and that none is relative (`TID252`).

### Visibility

A function, class or constant used only inside its module, and an attribute used only inside its
class, begins with an underscore; a name without one is part of what the module or the class
offers its callers. A test uses only names without one. Ruff reports an attribute with an
underscore used outside its class (`SLF001`); a name with an underscore imported from another
module it does not report yet, since its lint for that (`PLC2701`) is not stable.

### Interfaces between parts

An interface between parts - such as `Source` and `Dialect` - is an abstract class (`abc.ABC`) with
abstract methods, and its implementations derive from it: they say what they implement, and mypy
refuses to make an object of one that lacks a method. Ruff reports an abstract class without an
abstract method, and an empty method in one that is not marked abstract (`B024`, `B027`).
`typing.Protocol` is not used; ruff reports it (`TID251`).

### Small return values

A function that returns two values, called from a few places close to it - inside its module or
package, not a public interface - returns a tuple, not a class made for it. A class that only
bundles a return value is one more name to read and keep. A class is worth it once the value has a
meaning of its own: it gets methods, travels further than its caller, is stored or serialized, has
more than two parts, or its parts have the same type and could be swapped unnoticed.

### States are types

Fields that make sense only in certain combinations - two booleans of which only three combinations
occur, an optional field that is set exactly when another field has a certain value - become one
type whose variants hold what belongs to them. States that carry nothing are an `enum.Enum`; states
that carry something are a frozen dataclass each, joined in a union (`type Answer = Accepted |
Refused`) and told apart by `match`. A state that cannot be represented needs no check at its
callers. The same holds for parameters: a boolean that switches a function between two behaviours
becomes two functions, or an enum that names the behaviours.

### Services are held, not fetched

A class takes the services it works with - connections, clients, the configuration it reads - when
it is made, and keeps them as attributes:

*   **Constructor injection.** `__init__` takes the services; none is fetched again at every use,
    and none sits in a variable of its module, which would hide the dependency and tie every test
    to one instance.
*   **What it holds says what it needs.** A class holds the services it uses, not an object that
    reaches all of them. Several services that go together travel as a small context holding
    exactly those, never as one that holds everything again.
*   **No threading next to the owner.** A service is not passed into a function beside the object
    that already holds it; the function becomes a method of that object, or takes the object.

## Error handling

Errors carry what failed, and only what may be shown goes to users.

### Types of errors

*   An interface between parts answers an exception class of its own, derived from `Exception`
    and defined beside the interface - `SourceError` for `Source`: who implements it is not fixed,
    and its caller has to tell its errors apart. The class and its subclasses are the contract:
    what the caller can distinguish - what may be shown, a refusal, a failure of a backend.
*   An exception of a library is translated where the library is called, into the exception of
    the interface, keeping its cause: `raise SourceError("…") from error`.
*   `except Exception` is written only where errors are gathered and passed on - in `cli`, which
    logs them -, not at the boundary to implementations of others. Ruff reports it unless the
    handler raises again or logs the traceback (`BLE001`); in `cli` it is silenced, with its
    reason.
*   An expected failure never ends the program and is never silently dropped: it is passed on or
    handled. Ruff reports an exception passed over by `pass` or `continue`, of whatever class
    (`S110`, `S112`). Ending the program is for broken invariants alone; `sys.exit` is called in
    `cli` alone, and reported everywhere else (`TID251`).

### Messages name what failed

*   An error caused by configuration names the setting and where it is set.
*   An error caused by a remote system names the endpoint, without credentials, query or fragment,
    and the chain of its causes.
*   Messages never contain secret values or values of the database, because they are shown to
    users and logged above `debug`. A value in the cause of an error - the message of a database
    error - reaches the log with the traceback, at `debug` (see [Logging](#content)). Files and
    paths may be named: the tool runs on the machine of the user who reads them.

### What users see

What users may see of an error is the message of an exception class of the project, `str(error)`,
decided by whoever defines the class, in one place each, not by each caller. `cli` shows users that
message alone; of any other exception, that the run failed unexpectedly. The traceback goes to the
log at `debug`.

### Files are written whole

A file the tool writes - a profile, a sample, a report - is written whole or not at all: into a
temporary file next to it, which then takes its place (`os.replace`). A run that fails part of the
way leaves no half-written file behind, and the file of an earlier run intact. The tool never writes
to the database.

## Logging

### Setup

*   Every module logs through `logging` of the standard library, by a logger of its own name:
    `_logger = logging.getLogger(__name__)`. Nothing is printed - not by `print`, nor to
    `sys.stdout` or `sys.stderr`; ruff reports either (`T20`, `TID251`).
*   Only `cli` configures where logs go, in one place: to standard error. Ruff reports the
    configuration of the log anywhere else (`TID251`). `cli` reports the progress of a run through
    the log as well, at `info`; the command line has no output of its own besides the files it
    writes.

### Levels

*   **error** only for failures that abort an operation.
*   **warning** for degraded but continuing operation: a table that cannot be read, a detector that
    fails on a column.
*   **info** for the progress of a run: a stage or a table starting and finishing.
*   **debug** for detail: the SQL statements sent, the steps per column, the traceback of an error
    shown to users, values of the database. Python has no level below it.

### Content

*   **Values of the database are logged at `debug` alone** - those of a sample, an enum or a range,
    and those in the message of a database error or in a traceback. The log stays on the machine,
    as the workspace does. Above `debug`, what is logged is the names of tables and columns,
    counts, sizes and durations.
*   SQL statements are logged at `debug`.
*   Credentials and passwords are never logged, at any level.

## Testing

A test uses what the code offers its callers. One that needs an internal - a name with an
underscore, or one made public for it - says that a cut is wrong: it is a
[finding](../AGENTS.md#findings), and the visibility is not widened for it.

*   **Where tests live:** the tests of a project are in `tests/` beside its `src/` - `tests/` for
    the tool, `simulation/tests/` for the generator -, one file `test_<module>.py` per module, and a
    test of every module alike in a file named after what it checks. Pytest imports a test module by
    its name, so the names of test modules are unique across both directories; its mode `importlib`,
    which would not need that, takes the directory `simulation/` for the package of the same name,
    and hides it. A directory of tests is added to `testpaths` of pytest and to `files` of mypy with
    its first test: neither tool finds it on its own, and a test that does not run checks nothing.
*   **Shared fixtures:** what the tests of several modules use lives in one place, as a fixture in
    the `conftest.py` of the directory whose tests share it, built through the interface of the
    module whose things it builds. A test builds what it needs as the code does, from defaults, and
    writes only what it differs in. With a `conftest.py` in both directories of tests, mypy needs
    `explicit_package_bases` to tell them apart; it is set with the second one.
*   **Naming:** a test is named after what it shows, as a sentence after the `test_` pytest asks
    for: `test_a_profile_written_and_read_is_unchanged`. The name is its description: the
    functions of a test module - tests, fixtures, helpers - need no docstring, the module does.
*   **Assertions** say what was expected, in their message where the assertion alone does not:
    `assert …, "…"`.
*   **The simulation environment:** a test that needs it expects it to run, and fails if it does
    not. A test that skips itself hides that nothing was checked.
