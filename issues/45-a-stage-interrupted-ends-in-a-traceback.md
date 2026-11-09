# 45 — A stage interrupted ends in a traceback

**Status:** done
**Type:** bug
**Priority:** low
**Area:** Command line
**Summary:** A command stopped by Ctrl-C ends in the traceback of Python on standard error, though users are to see of a failure its message alone and the traceback goes to the log at `debug`.

## The problem

`run` of `data_profiler.commands`, the frame of every command line of the project, catches the
errors whose message may be shown and `Exception`. `KeyboardInterrupt` derives from `BaseException`,
so that it passes both: Python prints its traceback and ends the program.

## Why it matters

*What users see* in `docs/CODING-GUIDELINES.md` says that users are shown a message, and that the
traceback goes to the log at `debug`. Stopping a run by Ctrl-C is no accident, moreover: `scan` and
`describe` are documented as resumed after they are interrupted, and `adopt`
([44](44-merging-the-glossary-proposed-into-the-overrides.md)) is the first stage at which a person
is expected to stop midway, between two questions, the answers given being kept already.

Nothing is lost at present; what is wrong is what the person sees.

## Considerations

- **In the frame, for every command.** `run` catches `KeyboardInterrupt`, logs that the command was
  interrupted, the traceback at `debug` as for every failure, and ends the program. Recommended: it
  is one place, and the simulation's command line gets it as well.
- **In `adopt` alone,** as `AdoptError`, as where its input ends. It would leave the other stages as
  they are, and be a second way of doing one thing.
- **The exit code.** The module docs of `commands` say code 1 when the work fails. An interrupted
  program ends by convention with 130 (128 and the number of the signal), which is what Python
  gives today and what a shell script can tell apart from a failure. Recommended: 130, and the
  module docs say so.

## Done when

- A command stopped by Ctrl-C shows one line of the log and no traceback, and has the traceback in
  the log at debug level.
- Its exit code is the one decided, and a test of `commands` shows both.
- What was written before the interruption stays as it is.

## History

- **2026-11-09** — Opened, as the maintainer asked, from a finding of the review of
  [44](44-merging-the-glossary-proposed-into-the-overrides.md).

- **2026-11-09** — Done in the frame, for every command, the message at `info` as an interruption
  is no failure. The exit code differs from what was recommended above: Python does not exit with
  130 today, it ends by the signal, which a shell reports as 130, and a shell goes on with the next
  command of a script after a program that exits, whatever the code, which was tried:
  `sys.exit(130)` let the step after an interrupted command run. `run` therefore raises the signal
  again once it has logged, and ends as Python does, the script stopping with it. What was written
  stays as it is by `write_whole`, unchanged. At a question of `adopt` the line of the log follows
  the `^C` of the terminal on the same line; left so, as an end of the line would be output beside
  the log.
