"""The stage `adopt`: the concepts a profile proposes taken into the overrides, as a person answers.

It goes through the concepts `describe` proposed, in the order of the glossary of the profile, and
asks about what each adds to the concepts given, as `Overrides.adoptable` says: first its
description, then its abbreviations. A question is answered `Y`, `N` or `M`, in upper or lower case,
any other answer being asked again. `Y` takes what is proposed, the abbreviations proposed joining
those given; `N` leaves it, to be asked about again at the next run; `M` takes what the person
enters: a description, or all abbreviations of the concept in one line, separated by commas, in
place of those given and in lower case, nothing entered being asked again. A concept that adds
nothing is only logged.

Each answer is written at once, by `Overrides.amend`: to the file that gives the field, else to the
first that names the concept, a new concept to `Project.glossary_file`. The overrides are read anew
for each concept, so that a concept adopted takes its terms from the proposals after it, and a run
interrupted keeps the answers given and asks only what is left. The profile is not written.

The questions go through the function given as `ask`, `input` at the command line: they are the one
output of the tool besides its files and its log.
"""

import logging
from collections.abc import Callable, Mapping
from typing import Final

from data_profiler.overrides import Overrides
from data_profiler.profile import Concept
from data_profiler.project import Project

_logger = logging.getLogger(__name__)

_CHOICES: Final = ("Y", "N", "M")


class AdoptError(Exception):
    """An adoption that cannot go on, as its input is no terminal or ended."""


def adopt(glossary: Mapping[str, Concept], project: Project, ask: Callable[[str], str]) -> None:
    """Asks about each concept proposed in `glossary`, writing each answer to the overrides.

    Args:
        glossary: The concepts proposed, by their words: the glossary of a profile.
        project: The project, whose overrides are read and written.
        ask: Shows a question, and gives the line answered; raises `EOFError` where input ended.

    Raises:
        AdoptError: The input ended; the answers given so far are written.
        OverridesError: The overrides cannot be read, or an answer cannot be written to them.
    """
    asking = _Asking(project, ask)
    for word, proposed in glossary.items():
        asking.adopt(word, proposed)


class _Asking:
    """The questions of an adoption, and where their answers go."""

    def __init__(self, project: Project, ask: Callable[[str], str]) -> None:
        """Takes the project written to, and what asks the person."""
        self._project = project
        self._ask = ask

    def adopt(self, word: str, proposed: Concept) -> None:
        """Asks about what the concept `proposed` of `word` adds, writing each answer."""
        overrides = Overrides.read(self._project.overrides)
        adoptable = overrides.adoptable(word, proposed)
        if adoptable == Concept():
            _logger.info("Nothing to adopt of the concept %s", word)
            return
        if adoptable.description is not None:
            question = f'{word}: no description given, add "{adoptable.description}"?'
            prompt = f"The description of {word}: "
            answer = self._answer(question, adoptable.description, prompt, str)
            self._write(word, "description", answer)
        if adoptable.abbreviations:
            given = overrides.glossary.get(word, Concept()).abbreviations
            question = (
                f"{word}: abbreviations given [{', '.join(given)}],"
                f" add [{', '.join(adoptable.abbreviations)}]?"
            )
            prompt = f"All abbreviations of {word}, separated by commas: "
            answers = self._answer(
                question, (*given, *adoptable.abbreviations), prompt, _abbreviations
            )
            self._write(word, "abbreviations", answers)

    def _answer[Value](
        self, question: str, proposed: Value, prompt: str, entered: Callable[[str], Value]
    ) -> Value | None:
        """What is answered to `question`: `proposed`, None for no, or what is `entered`.

        Args:
            question: The question, of which `Y`, `N` or `M` are asked.
            proposed: What `Y` takes.
            prompt: What is shown to ask for what `M` takes.
            entered: Makes what `M` takes of the line entered; nothing where it is empty, of which
                the line is asked again.

        Returns:
            `proposed` at `Y`, None at `N`, what is entered at `M`.
        """
        while (choice := self._line(f"{question} [Y/N/M] ").upper()) not in _CHOICES:
            _logger.info("The answer is one of %s", ", ".join(_CHOICES))
        if choice == "N":
            return None
        if choice == "Y":
            return proposed
        while not (value := entered(self._line(prompt))):
            _logger.info("Nothing was entered")
        return value

    def _line(self, prompt: str) -> str:
        """The line answered to `prompt`, without the spaces around it."""
        try:
            return self._ask(prompt).strip()
        except EOFError as error:
            raise AdoptError("the input ended before every concept was asked about") from error

    def _write(self, word: str, field: str, answer: str | tuple[str, ...] | None) -> None:
        """Writes `answer` as the field `field` of the concept `word`, nothing where it is None."""
        if answer is not None:
            paths = self._project.overrides
            Overrides.amend(paths, ("glossary", word, field), answer, self._project.glossary_file)


def _abbreviations(line: str) -> tuple[str, ...]:
    """The abbreviations of `line`, separated by commas, in lower case, each once."""
    return tuple(dict.fromkeys(part.strip().lower() for part in line.split(",") if part.strip()))
