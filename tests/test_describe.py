"""Tests of the stage describe: the names of a profile split, concepts proposed, and names read."""

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.describe import describe, forgotten
from data_profiler.detect import Sensitivity
from data_profiler.glossary import Glossary, occurrences
from data_profiler.model import Model, ModelError
from data_profiler.overrides import ColumnOverride, Overrides, TableOverride
from data_profiler.profile import Column, Concept, Profile, Statistics, Table, Term, Value
from data_profiler.scan import scan
from data_profiler.source import Source
from data_profiler.workspace import Sample, Workspace

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm" / "overrides.yml"


class _Answers(Model):
    """A model that answers with the texts given, in their order, then with no concept at all."""

    def __init__(self, *answers: str) -> None:
        super().__init__("answers")
        self.prompts: list[str] = []
        self._answers = list(answers)

    def answer(self, prompt: str, form: Mapping[str, object]) -> str:
        self.prompts.append(prompt)
        return self._answers.pop(0) if self._answers else "{}"


class _Failing(Model):
    """A model that answers once with the text given, and fails then."""

    def __init__(self, answer: str) -> None:
        super().__init__("failing")
        self._answer: str | None = answer

    def answer(self, prompt: str, form: Mapping[str, object]) -> str:
        answer, self._answer = self._answer, None
        if answer is None:
            raise ModelError("the model fails")
        return answer


def _proposal(word: str, description: str = "") -> str:
    """The answer of a model that proposes the concept of `word`."""
    return json.dumps({"word": word, "description": description})


def _profile(*names: str, glossary: dict[str, Concept] | None = None) -> Profile:
    """A profile of a table `cust` of columns of `names`, of the concepts `glossary`."""
    columns = tuple(Column(name, "varchar(10)", Statistics(0, 1)) for name in names)
    table = Table(name="cust", rows=1, columns=columns)
    return Profile(catalog="crm", schema="sales", tables=(table,), glossary=glossary or {})


def _described(
    profile: Profile,
    tmp_path: Path,
    overrides: Overrides | None = None,
    model: Model | None = None,
    samples: dict[str, Sample] | None = None,
) -> Profile:
    """`profile` described by `model`, of the samples `samples`, else of none, as written."""
    workspace = Workspace.open(tmp_path / "workspace", profile.catalog, profile.schema)
    for table in profile.tables:
        sample = (samples or {}).get(table.name, Sample({c.name: [] for c in table.columns}))
        workspace.write_sample(table.name, sample)
    directory = tmp_path / "profile"
    describe(profile, overrides or Overrides(), model or _Answers(), workspace, directory)
    return Profile.read(directory)


# The concepts of the profiles of these tests, of an abbreviation of two among them.
_GLOSSARY = {
    "customer": Concept(("cust",)),
    "status": Concept(("st",)),
    "street": Concept(("st",)),
    "code": Concept(("cd",)),
    "name": Concept(("nm",)),
}


def test_a_name_is_split_into_its_terms_each_with_its_candidates(tmp_path: Path) -> None:
    profile = _profile("cust_st_cd", "addr2", glossary=_GLOSSARY)
    (table,) = _described(profile, tmp_path).tables
    assert table.terms == (Term("cust", ("customer",)),)
    split, digits = table.columns
    assert split.terms == (
        Term("cust", ("customer",)),
        Term("st", ("status", "street")),
        Term("cd", ("code",)),
    )
    assert digits.terms == (Term("addr"), Term("2")), "a term of no concept, and of digits"


def test_a_name_of_one_candidate_for_each_term_is_read_and_any_other_not(tmp_path: Path) -> None:
    profile = _profile("cust_nm", "cust_st_cd", "cust2", "cust_addr", glossary=_GLOSSARY)
    (table,) = _described(profile, tmp_path).tables
    assert table.reading == ("customer",)
    assert [column.reading for column in table.columns] == [
        ("customer", "name"),
        None,
        ("customer", "2"),
        None,
    ], "a term of two concepts and one of none are not read"


def test_a_reading_that_agrees_with_the_terms_of_its_name_is_kept(tmp_path: Path) -> None:
    (table,) = _described(_profile("st_cd", glossary=_GLOSSARY), tmp_path / "first").tables
    chosen = replace(table.columns[0], reading=("street", "code"))
    profile = replace(_profile(glossary=_GLOSSARY), tables=(replace(table, columns=(chosen,)),))
    (again,) = _described(profile, tmp_path / "second").tables
    assert again.columns[0].reading == ("street", "code"), "as chosen, a split that stayed"
    stale = replace(chosen, reading=("street", "name"))
    profile = replace(profile, tables=(replace(table, columns=(stale,)),))
    (again,) = _described(profile, tmp_path / "third").tables
    assert again.columns[0].reading is None, "a reading that no longer agrees is none"


def test_the_concepts_of_the_overrides_count_but_the_profile_holds_nothing_of_them(
    tmp_path: Path,
) -> None:
    given = TableOverride(columns={"cust_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL)})
    overrides = Overrides(glossary={"customer": Concept(("cust",))}, tables={"cust": given})
    profile = _profile("cust_nm", glossary={"name": Concept(("nm",))})
    model = _Answers()
    described = _described(profile, tmp_path, overrides, model)
    (column,) = described.tables[0].columns
    assert column.reading == ("customer", "name"), "by the concept given"
    assert column.marked is None, "the mark given is laid over by the stage that reads it"
    assert described.glossary == profile.glossary
    assert model.prompts == [], "no term of a concept given is asked for"


def test_a_reading_given_counts_once_the_name_is_split(tmp_path: Path) -> None:
    given = TableOverride(
        columns={"cust_st_cd": ColumnOverride(reading=("customer", "status", "code"))}
    )
    overrides = Overrides(tables={"cust": given})
    profile = _profile("cust_st_cd", glossary=_GLOSSARY)
    laid = overrides.laid_over(profile)
    assert Glossary(laid.glossary).harmonized(laid.tables[0].columns[0]) is None, "not split"
    laid = overrides.laid_over(_described(profile, tmp_path, overrides))
    assert Glossary(laid.glossary).harmonized(laid.tables[0].columns[0]) == "customer_status_code"


def test_a_term_of_no_concept_is_of_the_concept_the_model_proposes(tmp_path: Path) -> None:
    model = _Answers(_proposal("Delivery Address", " Where an order is delivered to. "))
    samples = {"cust": Sample({"cust_dlvadr": ["Hauptstr. 1", None, "", "Hauptstr. 1", "Ring 2"]})}
    profile = _profile("cust_dlvadr", glossary={"customer": Concept(("cust",))})
    (table,) = profile.tables
    (column,) = table.columns
    # Its empty texts left aside as sentinels, as scan counted them.
    counted = replace(column, statistics=Statistics(1, 2, sentinels=(Value("", 1),)))
    profile = replace(profile, tables=(replace(table, columns=(counted,)),))
    described = _described(profile, tmp_path, model=model, samples=samples)
    assert described.glossary["delivery_address"] == Concept(
        ("dlvadr",), "Where an order is delivered to."
    ), "its word as a name is written, its description without spaces at either end"
    (column,) = described.tables[0].columns
    assert column.reading == ("customer", "delivery_address"), "split again, and read"
    (prompt,) = model.prompts
    assert '"dlvadr"' in prompt
    assert "- column cust.cust_dlvadr: varchar(10); values: Hauptstr. 1, Ring 2" in prompt, (
        "but its nulls and sentinels"
    )


def test_a_word_the_glossary_has_takes_the_term_as_one_more_abbreviation(tmp_path: Path) -> None:
    glossary = {"customer": Concept(("cust",)), "address": Concept(("addr",), "Where one lives.")}
    profile = _profile("cust_addr", "cust_adr", glossary=glossary)
    described = _described(profile, tmp_path, model=_Answers(_proposal("address", "Other.")))
    assert described.glossary["address"] == Concept(("addr", "adr"), "Where one lives.")
    assert [column.reading for column in described.tables[0].columns] == [
        ("customer", "address"),
        ("customer", "address"),
    ]


def test_the_values_of_a_column_of_a_sensitivity_are_not_shown_to_the_model(
    tmp_path: Path,
) -> None:
    marked = TableOverride(columns={"cust_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL)})
    model = _Answers()
    samples = {"cust": Sample({"cust_nm": ["Anna Muster"]})}
    _described(_profile("cust_nm"), tmp_path, Overrides(tables={"cust": marked}), model, samples)
    assert len(model.prompts) == 2, "of cust and of nm"
    assert all("Anna" not in prompt for prompt in model.prompts)
    assert (
        "- column cust.cust_nm: varchar(10); personal data, its values not shown"
        in (model.prompts[1])
    )


def test_an_answer_not_of_the_form_asked_for_is_passed_over(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    profile = _profile("cust_addr", glossary={"customer": Concept(("cust",))})
    described = _described(profile, tmp_path, model=_Answers("an address", _proposal("_")))
    assert described.glossary == profile.glossary
    assert "An answer of answers was not of the form asked for" in caplog.messages
    assert "No concept was proposed of the term addr" in caplog.messages


def test_only_the_terms_of_no_concept_are_asked_for(tmp_path: Path) -> None:
    profile = _profile("cust_addr", glossary={"customer": Concept(("cust",))})
    described = _described(profile, tmp_path, model=_Answers(_proposal("address")))
    model = _Answers()
    _described(described, tmp_path, model=model)
    assert model.prompts == [], "nothing is asked for again"


def test_the_profile_is_written_after_each_concept_proposed(tmp_path: Path) -> None:
    profile = _profile("cust_addr")
    with pytest.raises(ModelError):
        _described(profile, tmp_path, model=_Failing(_proposal("customer")))
    written = Profile.read(tmp_path / "profile")
    assert written.glossary == {"customer": Concept(("cust",))}, "before the model failed"


def test_the_abbreviations_no_name_has_any_longer_are_dropped(tmp_path: Path) -> None:
    glossary = {"customer": Concept(("cust", "kd")), "order": Concept(("ord",))}
    described = _described(_profile("cust_nm", glossary=glossary), tmp_path)
    assert described.glossary == {"customer": Concept(("cust",))}, "and a concept of none left"


def test_a_profile_forgotten_has_no_glossary_and_no_readings(tmp_path: Path) -> None:
    described = _described(_profile("cust_nm", glossary=_GLOSSARY), tmp_path)
    profile = forgotten(described)
    assert profile.glossary == {}
    (table,) = profile.tables
    assert table.reading is None
    assert [(c.terms, c.reading) for c in table.columns] == [
        (described.tables[0].columns[0].terms, None)
    ], "its terms as they were split"


def test_the_names_of_the_example_are_read_from_words_given(
    example_profile: Profile, tmp_path: Path
) -> None:
    glossary = {f"word_{term}": Concept((term,)) for term in occurrences(example_profile)}
    model = _Answers()
    described = _described(replace(example_profile, glossary=glossary), tmp_path, model=model)
    assert model.prompts == []
    words = Glossary(glossary)
    for table in described.tables:
        for column in table.columns:
            assert column.terms is not None, column.name
            expected = "_".join(
                term.text if term.text.isdigit() else f"word_{term.text}" for term in column.terms
            )
            assert words.harmonized(column) == expected, column.name


def test_the_names_of_the_example_are_read_with_its_overrides(
    example_profile: Profile, tmp_path: Path
) -> None:
    overrides = Overrides.read(_EXAMPLE)
    laid = overrides.laid_over(_described(example_profile, tmp_path, overrides))
    glossary = Glossary(laid.glossary)
    columns = {c.name: c for c in laid.tables[1].columns}
    assert laid.tables[1].name == "cust"
    assert glossary.harmonized(columns["ap_ap_nm"]) == "contact_person_name", (
        "a term repeated in two meanings, by the reading given"
    )
    assert glossary.harmonized(columns["cust_ap_id"]) == "customer_contact_person_identifier"
    assert glossary.harmonized(columns["ap_seg_cd"]) == "segment_code", "the prefix omitted"


def test_a_scan_keeps_the_terms_and_readings_describe_filled(
    source: Source, tmp_path: Path
) -> None:
    workspace = Workspace.open(tmp_path / "workspace", "crm", "sales")
    directory = tmp_path / "profile"
    pattern = re.compile("cust")
    scan(source, pattern, workspace, (), Overrides(), directory)
    concepts = {"customer": Concept(("cust",)), "identifier": Concept(("id",))}
    describe(
        Profile.read(directory), Overrides(glossary=concepts), _Answers(), workspace, directory
    )
    described = Profile.read(directory)
    scan(source, pattern, workspace, (), Overrides(), directory)
    (table,) = Profile.read(directory).tables
    (before,) = described.tables
    assert table.run != before.run, "counted anew"
    assert (table.terms, table.reading) == (before.terms, before.reading)
    assert [(c.terms, c.reading) for c in table.columns] == [
        (c.terms, c.reading) for c in before.columns
    ]
    assert table.columns[0].reading == ("customer", "identifier"), "of cust_id"


def test_the_log_of_describe_holds_no_values_above_debug(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    samples = {"cust": Sample({"cust_addr": ["Hauptstr. 1"]})}
    profile = _profile("cust_addr", glossary={"customer": Concept(("cust",))})
    _described(profile, tmp_path, model=_Answers(_proposal("address")), samples=samples)
    assert "Hauptstr" not in caplog.text
