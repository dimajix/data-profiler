"""Tests of the stage `adopt`: what is asked of the concepts proposed, and where it is written."""

import logging
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from data_profiler.adopt import AdoptError, adopt
from data_profiler.overrides import FORMAT, Overrides
from data_profiler.profile import Concept
from data_profiler.project import Project

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm"
_HEAD = f'format: "{FORMAT.version}"\n'
_PROPOSED = {"customer": Concept(("cust", "kd"), "Who buys.")}


class _Person:
    """Answers the questions asked by the lines given, and remembers them."""

    def __init__(self, *answers: str) -> None:
        self.questions: list[str] = []
        self._answers = list(answers)

    def __call__(self, question: str) -> str:
        self.questions.append(question)
        if not self._answers:
            raise EOFError
        return self._answers.pop(0)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    shutil.copy(_EXAMPLE / "project.yml", tmp_path)
    return Project.read(tmp_path, {})


def _written(project: Project, **files: str) -> Callable[[str], Path]:
    root = project.glossary_file.parents[1]
    (root / "overrides").mkdir(exist_ok=True)
    for name, text in files.items():
        (root / f"{name.replace('__', '/')}.yml").write_text(_HEAD + text, encoding="utf-8")
    return lambda name: root / f"{name.replace('__', '/')}.yml"


def _glossary(project: Project) -> dict[str, Concept]:
    return dict(Overrides.read(project.overrides).glossary)


def test_a_new_concept_answered_yes_goes_to_a_glossary_file_made_for_it(project: Project) -> None:
    adopt(_PROPOSED, project, _Person("Y", "Y"))
    assert _glossary(project) == _PROPOSED
    text = project.glossary_file.read_text(encoding="utf-8")
    assert text.startswith(_HEAD), "with the version of the format"


def test_a_new_concept_is_added_to_the_glossary_file_where_it_is_there(project: Project) -> None:
    _written(project, overrides__glossary="glossary:\n  order: {}\n")
    adopt(_PROPOSED, project, _Person("Y", "Y"))
    assert list(_glossary(project)) == ["order", "customer"]


def test_a_concept_answered_no_writes_nothing(project: Project) -> None:
    person = _Person("N", "N")
    adopt(_PROPOSED, project, person)
    assert len(person.questions) == 2, "of its description, then of its abbreviations"
    assert "Who buys." in person.questions[0]
    assert "cust, kd" in person.questions[1]
    assert not project.glossary_file.exists(), "no file for no answer"


def test_a_description_can_be_entered(project: Project) -> None:
    adopt(_PROPOSED, project, _Person("m", "  Who pays. ", "n"))
    assert _glossary(project) == {"customer": Concept((), "Who pays.")}


def test_abbreviations_entered_replace_those_given_in_lower_case_each_once(
    project: Project,
) -> None:
    _written(project, overrides="glossary:\n  customer: {abbreviations: [cst], description: B.}\n")
    adopt(_PROPOSED, project, _Person("M", " KD, cust,,kd "))
    assert _glossary(project)["customer"].abbreviations == ("kd", "cust")


def test_abbreviations_answered_yes_join_those_given(project: Project) -> None:
    _written(project, overrides="glossary:\n  customer: {abbreviations: [cst], description: B.}\n")
    adopt(_PROPOSED, project, _Person("y"))
    assert _glossary(project)["customer"] == Concept(("cst", "cust", "kd"), "B.")


def test_a_concept_that_adds_nothing_is_not_asked_about(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    _written(
        project, overrides="glossary:\n  customer: {abbreviations: [cust, kd], description: B.}\n"
    )
    before = _glossary(project)
    with caplog.at_level(logging.INFO):
        adopt(_PROPOSED, project, _Person())
    assert _glossary(project) == before
    assert caplog.messages == ["Nothing to adopt of the concept customer"], "a short message"


def test_a_description_given_stands_where_the_one_proposed_differs(project: Project) -> None:
    _written(project, overrides="glossary:\n  customer: {abbreviations: [cst], description: B.}\n")
    person = _Person("N")
    adopt(_PROPOSED, project, person)
    assert len(person.questions) == 1, "of its abbreviations alone"
    assert "Who buys." not in person.questions[0]


def test_abbreviations_given_that_are_not_proposed_are_no_difference(project: Project) -> None:
    given = "glossary:\n  customer: {abbreviations: [cust, kd, cst], description: B.}\n"
    _written(project, overrides=given)
    person = _Person()
    adopt(_PROPOSED, project, person)
    assert person.questions == [], "only what is proposed and not given is a difference"


def test_a_concept_given_without_a_description_is_asked_about_it(project: Project) -> None:
    file = _written(project, overrides="glossary:\n  customer: {abbreviations: [cust, kd]}\n")
    adopt(_PROPOSED, project, _Person("Y"))
    assert _glossary(project)["customer"] == Concept(("cust", "kd"), "Who buys.")
    assert "Who buys." in file("overrides").read_text(encoding="utf-8"), "the file naming it"
    assert not project.glossary_file.exists()


def test_a_field_is_written_to_the_file_that_gives_it_of_a_concept_spread_over_two(
    project: Project,
) -> None:
    file = _written(
        project,
        overrides="glossary:\n  customer:\n    description: B.\n",
        overrides__terms="glossary:\n  customer:\n    abbreviations: [cst]\n",
    )
    adopt(_PROPOSED, project, _Person("Y"))
    assert "kd" in file("overrides__terms").read_text(encoding="utf-8")
    assert "kd" not in file("overrides").read_text(encoding="utf-8")
    assert _glossary(project)["customer"] == Concept(("cst", "cust", "kd"), "B.")


def test_a_field_no_file_gives_goes_to_the_first_file_naming_the_concept(project: Project) -> None:
    file = _written(
        project,
        overrides__a="glossary:\n  customer: {abbreviations: [cust]}\n",
        overrides__b="glossary:\n  customer: {omitted: false}\n",
    )
    adopt({"customer": Concept(("cust",), "Who buys.")}, project, _Person("Y"))
    assert "Who buys." in file("overrides__a").read_text(encoding="utf-8")


def test_comments_of_a_file_written_are_kept(project: Project) -> None:
    text = "# Top.\nglossary:\n  # Those who buy.\n  customer: {abbreviations: [cst]}  # Short.\n"
    file = _written(project, overrides=text)
    adopt(_PROPOSED, project, _Person("Y", "Y"))
    written = file("overrides").read_text(encoding="utf-8")
    assert "# Top." in written
    assert "# Those who buy." in written
    assert "# Short." in written


def test_a_concept_adopted_takes_its_terms_from_the_proposals_after_it(project: Project) -> None:
    proposed = {"customer": Concept(("cust",), "Who buys."), "client": Concept(("cust",), "Who?")}
    person = _Person("Y", "Y")
    adopt(proposed, project, person)
    assert len(person.questions) == 2, "none of client, its terms being taken"
    assert list(_glossary(project)) == ["customer"]


def test_a_concept_whose_abbreviations_the_given_have_taken_is_not_asked_about(
    project: Project,
) -> None:
    _written(project, overrides="glossary:\n  customer: {abbreviations: [cust], description: B.}\n")
    person = _Person()
    adopt({"client": Concept(("cust",), "Who?")}, project, person)
    assert person.questions == [], "as it would be dropped where the overrides are laid over"


def test_a_word_proposed_as_its_own_abbreviation_is_not_offered_it(project: Project) -> None:
    person = _Person("Y")
    adopt({"iban": Concept(("iban",), "An account.")}, project, person)
    assert len(person.questions) == 1, "of its description alone"
    assert _glossary(project) == {"iban": Concept((), "An account.")}


def test_an_answer_of_no_choice_is_asked_again(project: Project) -> None:
    person = _Person("", "x", "n", "n")
    adopt(_PROPOSED, project, person)
    assert len(person.questions) == 4


@pytest.mark.parametrize(("description", "abbreviations"), [("", ""), ("  ", "  "), ("", " , ,")])
def test_nothing_entered_is_asked_again(
    project: Project, description: str, abbreviations: str
) -> None:
    adopt(_PROPOSED, project, _Person("m", description, "Who.", "m", abbreviations, "kd"))
    assert _glossary(project) == {"customer": Concept(("kd",), "Who.")}


def test_input_that_ends_stops_with_the_answers_given_kept(project: Project) -> None:
    with pytest.raises(AdoptError, match="the input ended"):
        adopt(_PROPOSED, project, _Person("Y"))
    assert _glossary(project) == {"customer": Concept((), "Who buys.")}


def test_words_that_yaml_reads_otherwise_are_written_so_as_to_be_read_as_texts(
    project: Project,
) -> None:
    adopt({"number": Concept(("no", "on"), None)}, project, _Person("Y"))
    assert _glossary(project)["number"].abbreviations == ("no", "on")
