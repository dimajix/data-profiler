# 22 — A condition of a column and a threshold of a type

**Status:** done
**Type:** refactoring
**Priority:** medium
**Area:** Detection
**Summary:** A detector judges each value on its own, against one threshold of all types, so that a type that shows only in the values of a column together - a pair of flags, free text - cannot be recognised.

## The problem

A `Detector` of `detect.py` recognises a value by its pattern and a check of it; `detect` counts
the values of a sample it recognises, and `matching.recognise` makes a type a match where the share
is at least `_MATCHING`, one half, for every type alike. Two types to come do not fit:

- **The pairs of flags** of [20](20-detectors-of-boolean-pairs.md): a value `0` or `1` is no flag
  by itself, a column of counts holds them too; what makes a column of flags is that it has at
  most two distinct values, or that every value is of the pair.
- **Free text** of [21](21-a-detector-of-free-text.md): a value of words is no free text by
  itself, a name has words too; what makes a column of comments is how its values are together -
  words in lower case, letters, distinct values -, and many of its values are short, so that half
  of them are not of words.

## Why it matters

Both issues build on this one: without a condition of a column and a threshold of a type, each
would add a special case of its own to `detect` or `matching`. Decided with the maintainer as one
concept for both, built as a refactoring of its own before either, without a change of behaviour.

## How

As proposed in the plan recorded in [21](21-a-detector-of-free-text.md), `Detector` stays the one
kind of detector, and gets two parts beside its pattern and its check:

```python
@dataclass(frozen=True)
class Detector:
    """Recognises one semantic type: by a pattern, a check of a value, and a condition of its column."""

    pattern: re.Pattern[str]
    check: Callable[[str], bool] | None = None
    column: Callable[[Sequence[str]], bool] | None = None
    """Whether the texts of a column, together, are of the type; None where each value says it alone."""
    threshold: float = 0.5
    """The share of the values of a sample of the type that makes it a match."""

    def recognises(self, value: str) -> bool: ...  # as now
    def share(self, texts: Sequence[str]) -> float:
        """The share of `texts` of the type; 0 where the column fails the condition."""
```

- **The share stays a share of values**, of those the pattern and the check recognise; the
  condition of the column is judged on the sample alone, and `verify` counts the pattern on the
  table as now, which the documentation of `Match.table` says.
- **`detect`** asks each detector for its `share`, so that the counting moves to the detector.
- **`matching.recognise`** compares the share with the threshold of the type, and `_MATCHING`
  goes.
- **`is_sensitive`** checks a value by `recognises`, as the condition of a column does not apply
  to a value alone.
- **The types of the tool** keep the threshold of one half and no condition, and **the types of
  a project** are of a pattern alone, as now; neither is given a threshold or a condition in
  `project.yml` until someone needs one.

The interface is put before the maintainer before it is built: the names `column` and
`threshold`, and whether the threshold is of the detector or of the semantic type.

## Done when

- `Detector.share` is tested with and without a condition of a column, and with a threshold other
  than one half.
- The tests pass unchanged otherwise: no type of the tool is recognised differently.
- The module documentation of `detect.py` and `matching.py`, and `docs/ARCHITECTURE.md` where it
  describes the detectors, say what a condition of a column and a threshold of a type are.

## History

- **2026-11-02** — Opened as the maintainer decided that the condition of a column and the
  threshold of a type become one concept for [20](20-detectors-of-boolean-pairs.md) and
  [21](21-a-detector-of-free-text.md), built before either.

- **2026-11-02** — Decided with the maintainer: the threshold is of the detector, not of the
  semantic type, as the condition of the column and the threshold together say when a detector
  recognises its type in a column; the names `column` and `threshold` as proposed.

- **2026-11-02** — Done as decided: `Detector` has the fields `column`, a condition of the column
  judged on the texts of a sample, called only where the detector recognises one of them or more,
  and `threshold`, one half unless another is given, and the method `share`, which `detect` asks;
  `matching.recognise` compares a share with the threshold of its detector, and `_MATCHING` is
  gone. No type of the tool has a condition or another threshold yet; the tests pass unchanged,
  the round trip with the simulation environment among them.

- **2026-11-02** — As the review found and the maintainer decided, the threshold is applied where
  it is kept: `detect` returns the types whose share reaches the threshold of their detector
  alone, so that `matching.recognise` no longer reaches into the detector, and no share below
  the threshold leaves `detect.py`.
