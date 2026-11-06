"""Tests of the stage describe: the names of a profile split, concepts proposed, and names read."""

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.describe import describe, forgotten
from data_profiler.detect import CURRENCY_CODE, Sensitivity
from data_profiler.glossary import Glossary, occurrences
from data_profiler.llm import LanguageModel, LanguageModelError
from data_profiler.overrides import ColumnOverride, Overrides, TableOverride
from data_profiler.profile import (
    Column,
    ColumnGroup,
    Concept,
    Findings,
    Lengths,
    Match,
    Profile,
    Range,
    Statistics,
    Table,
    Term,
    Value,
)
from data_profiler.scan import scan
from data_profiler.source import Source
from data_profiler.workspace import Sample, Workspace

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm" / "overrides.yml"


class _Answers(LanguageModel):
    """A model that answers with the texts given, in their order, then with nothing of the form.

    The questions of the descriptions of columns are kept apart from those of concepts and
    readings, and answered by the descriptions given.
    """

    def __init__(self, *answers: str, descriptions: tuple[str, ...] = ()) -> None:
        super().__init__("answers")
        self.prompts: list[str] = []
        self.forms: list[Mapping[str, object]] = []
        self.descriptions: list[str] = []
        self._answers = list(answers)
        self._descriptions = [json.dumps({"description": text}) for text in descriptions]

    def answer(self, prompt: str, form: Mapping[str, object]) -> str:
        if "Describe in one or two sentences" in prompt:
            self.descriptions.append(prompt)
            return self._descriptions.pop(0) if self._descriptions else "{}"
        self.prompts.append(prompt)
        self.forms.append(form)
        return self._answers.pop(0) if self._answers else "{}"


class _Failing(LanguageModel):
    """A model that answers once with the text given, and fails then."""

    def __init__(self, answer: str) -> None:
        super().__init__("failing")
        self.prompts: list[str] = []
        self._answer: str | None = answer

    def answer(self, prompt: str, form: Mapping[str, object]) -> str:
        self.prompts.append(prompt)
        answer, self._answer = self._answer, None
        if answer is None:
            raise LanguageModelError("the model fails")
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
    llm: LanguageModel | None = None,
    samples: dict[str, Sample] | None = None,
) -> Profile:
    """`profile` described by `llm`, of the samples `samples`, else of none, as written."""
    workspace = Workspace.open(tmp_path / "workspace", profile.catalog, profile.schema)
    for table in profile.tables:
        sample = (samples or {}).get(table.name, Sample({c.name: [] for c in table.columns}))
        workspace.write_sample(table.name, sample)
    directory = tmp_path / "profile"
    describe(profile, overrides or Overrides(), llm or _Answers(), workspace, directory)
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


def test_a_name_written_as_the_words_of_concepts_is_read_by_them(tmp_path: Path) -> None:
    profile = _profile("customer_name", "customername", glossary=_GLOSSARY)
    described = _described(profile, tmp_path)
    (table,) = described.tables
    assert [column.reading for column in table.columns] == [
        ("customer", "name"),
        ("customer", "name"),
    ], "written apart or together"
    assert described.glossary["name"] == Concept(()), "kept by its word, without its abbreviation"


def test_an_abbreviation_given_that_no_name_has_is_warned_of_once(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    overrides = Overrides(glossary={"order": Concept(("ord",))})
    _described(_profile("cust_nm", glossary=_GLOSSARY), tmp_path, overrides)
    warned = [
        message for message in caplog.messages if "that no name of the profile has" in message
    ]
    assert warned == [
        "The overrides give abbreviations, in lower case as terms are, that no name of the profile"
        " has: ord"
    ], "once a run, and the run goes on"


def test_without_a_model_the_names_are_split_and_read_by_their_candidates_alone(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    glossary = {**_GLOSSARY, "order": Concept(("ord",))}
    (table,) = _profile("cust_nm", "cust_st_cd", "xy_cd", "st_nm", glossary=glossary).tables
    nm, st_cd, xy_cd, st_nm = table.columns
    terms = (Term("cust", ("customer",)), Term("st", ("status", "street")), Term("cd", ("code",)))
    chosen = replace(st_cd, terms=terms, reading=("customer", "street", "code"))
    columns = (replace(nm, description="Filled before."), chosen, xy_cd, st_nm)
    profile = replace(_profile(glossary=glossary), tables=(replace(table, columns=columns),))
    workspace = Workspace.open(tmp_path / "workspace", profile.catalog, profile.schema)
    describe(profile, Overrides(), None, workspace, tmp_path / "profile")
    described = Profile.read(tmp_path / "profile")
    (table,) = described.tables
    assert [column.reading for column in table.columns] == [
        ("customer", "name"),
        ("customer", "street", "code"),
        None,
        None,
    ], "a reading chosen before kept, a term of no concept and one of two left unread"
    assert table.columns[2].terms == (Term("xy"), Term("cd", ("code",))), "split all the same"
    assert table.columns[0].description == "Filled before.", "kept"
    assert table.columns[1].description is None, "none proposed"
    assert "order" not in described.glossary, "a concept of no term dropped"
    assert "xy" not in {t for concept in described.glossary.values() for t in concept.abbreviations}
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING], "no answer missed"


def test_a_reading_is_kept_while_the_terms_of_its_name_stay_as_they_were_split(
    tmp_path: Path,
) -> None:
    (table,) = _described(_profile("st_cd", glossary=_GLOSSARY), tmp_path / "first").tables
    chosen = replace(table.columns[0], reading=("street", "code"))
    profile = replace(_profile(glossary=_GLOSSARY), tables=(replace(table, columns=(chosen,)),))
    llm = _Answers()
    (again,) = _described(profile, tmp_path / "second", llm=llm).tables
    assert again.columns[0].reading == ("street", "code"), "as chosen, a split that stayed"
    assert llm.prompts == [], "not asked for again"
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
    llm = _Answers()
    described = _described(profile, tmp_path, overrides, llm)
    (column,) = described.tables[0].columns
    assert column.reading == ("customer", "name"), "by the concept given"
    assert column.marked is None, "the mark given is laid over by the stage that reads it"
    assert described.glossary == profile.glossary
    assert llm.prompts == [], "no term of a concept given is asked for"


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
    llm = _Answers(_proposal("Delivery Address", " Where an order is delivered to. "))
    samples = {"cust": Sample({"cust_dlvadr": ["Hauptstr. 1", None, "", "Hauptstr. 1", "Ring 2"]})}
    profile = _profile("cust_dlvadr", glossary={"customer": Concept(("cust",))})
    (table,) = profile.tables
    (column,) = table.columns
    # Its empty texts left aside as sentinels, as scan counted them.
    counted = replace(column, statistics=Statistics(1, 2, sentinels=(Value("", 1),)))
    profile = replace(profile, tables=(replace(table, columns=(counted,)),))
    described = _described(profile, tmp_path, llm=llm, samples=samples)
    assert described.glossary["delivery_address"] == Concept(
        ("dlvadr",), "Where an order is delivered to."
    ), "its word as a name is written, its description without spaces at either end"
    (column,) = described.tables[0].columns
    assert column.reading == ("customer", "delivery_address"), "split again, and read"
    (prompt,) = llm.prompts
    assert '"dlvadr"' in prompt
    assert "- column cust.cust_dlvadr: varchar(10); values: Hauptstr. 1, Ring 2" in prompt, (
        "but its nulls and sentinels"
    )


def test_a_word_the_glossary_has_takes_the_term_as_one_more_abbreviation(tmp_path: Path) -> None:
    glossary = {"customer": Concept(("cust",)), "address": Concept(("addr",), "Where one lives.")}
    profile = _profile("cust_addr", "cust_adr", glossary=glossary)
    described = _described(profile, tmp_path, llm=_Answers(_proposal("address", "Other.")))
    assert described.glossary["address"] == Concept(("addr", "adr"), "Where one lives.")
    assert [column.reading for column in described.tables[0].columns] == [
        ("customer", "address"),
        ("customer", "address"),
    ]


def test_the_values_of_a_column_of_a_sensitivity_are_not_shown_to_the_model(
    tmp_path: Path,
) -> None:
    marked = TableOverride(columns={"cust_nm": ColumnOverride(sensitivity=Sensitivity.PERSONAL)})
    llm = _Answers()
    samples = {"cust": Sample({"cust_nm": ["Anna Muster"]})}
    _described(_profile("cust_nm"), tmp_path, Overrides(tables={"cust": marked}), llm, samples)
    assert len(llm.prompts) == 2, "of cust and of nm"
    assert all("Anna" not in prompt for prompt in (*llm.prompts, *llm.descriptions))
    assert (
        "- column cust.cust_nm: varchar(10); personal data, its values not shown"
        in (llm.prompts[1])
    )


def test_an_answer_not_of_the_form_asked_for_is_passed_over(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    profile = _profile("cust_addr", glossary={"customer": Concept(("cust",))})
    described = _described(profile, tmp_path, llm=_Answers("an address", _proposal("_")))
    assert described.glossary == profile.glossary
    assert "An answer of answers was not of the form asked for" in caplog.messages
    assert "No concept was proposed of the term addr" in caplog.messages


def test_only_the_terms_of_no_concept_are_asked_for(tmp_path: Path) -> None:
    profile = _profile("cust_addr", glossary={"customer": Concept(("cust",))})
    described = _described(profile, tmp_path, llm=_Answers(_proposal("address")))
    llm = _Answers()
    _described(described, tmp_path, llm=llm)
    assert llm.prompts == [], "nothing is asked for again"


def test_the_profile_is_written_after_each_concept_proposed(tmp_path: Path) -> None:
    profile = _profile("cust_addr")
    with pytest.raises(LanguageModelError):
        _described(profile, tmp_path, llm=_Failing(_proposal("customer")))
    written = Profile.read(tmp_path / "profile")
    assert written.glossary == {"customer": Concept(("cust",))}, "before the model failed"


def test_a_name_of_a_term_of_several_concepts_is_read_by_the_model(tmp_path: Path) -> None:
    glossary = {**_GLOSSARY, "street": Concept(("st",), "Where a building stands.")}
    llm = _Answers(json.dumps({"2_st": "street"}))
    described = _described(_profile("cust_st_cd", glossary=glossary), tmp_path, llm=llm)
    (column,) = described.tables[0].columns
    assert column.reading == ("customer", "street", "code")
    (prompt,) = llm.prompts
    assert 'the column "cust_st_cd" of the table "cust": varchar(10).' in prompt
    assert '- "st" (2_st): one of status; street (Where a building stands.)' in prompt
    assert '- "cust" (1_cust): customer' in prompt
    assert llm.forms[0]["properties"] == {"2_st": {"type": "string", "enum": ["status", "street"]}}


def test_the_model_is_shown_what_the_database_and_a_table_hold_where_it_is_given(
    tmp_path: Path,
) -> None:
    overrides = Overrides(
        description="The CRM of a wholesaler.",
        tables={"cust": TableOverride(description="The customers of the wholesaler.")},
    )
    llm = _Answers(
        _proposal("type"), json.dumps({"3_st": "status"}), descriptions=("Its type.", "Its kind.")
    )
    profile = _profile("cust_typ_st", "typ", glossary=_GLOSSARY)
    described = _described(profile, tmp_path, overrides, llm)
    concept, reading = llm.prompts
    description, _ = llm.descriptions
    for prompt in (concept, reading, description):
        assert "\nWhat the database holds: The CRM of a wholesaler.\n" in prompt
    assert concept.count("- cust: The customers of the wholesaler.") == 1, "the table once"
    assert "What the tables hold:\n- cust: The customers of the wholesaler.\n" in concept
    assert 'What the table "cust" holds: The customers of the wholesaler.\nIt is about' in reading
    assert "- what the table holds: The customers of the wholesaler.\n" in description
    assert described.description is None, "the profile written holds nothing of the overrides"
    assert described.tables[0].description is None


def test_a_term_repeated_in_two_meanings_is_read_in_each(tmp_path: Path) -> None:
    glossary = {
        "customer": Concept(("cust",)),
        "airplus": Concept(("ap",)),
        "contact": Concept(("ap",)),
        "name": Concept(("nm",)),
    }
    llm = _Answers(json.dumps({"1_ap": "airplus", "2_ap": "contact"}))
    described = _described(_profile("ap_ap_nm", glossary=glossary), tmp_path, llm=llm)
    assert described.tables[0].columns[0].reading == ("airplus", "contact", "name")


def test_a_choice_of_no_candidate_is_passed_over(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    llm = _Answers(json.dumps({"2_st": "stone"}))
    described = _described(_profile("cust_st_cd", glossary=_GLOSSARY), tmp_path, llm=llm)
    assert described.tables[0].columns[0].reading is None
    assert "No reading was chosen of the name cust_st_cd" in caplog.messages


def test_a_name_whose_reading_is_given_is_not_asked_for(tmp_path: Path) -> None:
    given = TableOverride(
        columns={"cust_st_cd": ColumnOverride(reading=("customer", "status", "code"))}
    )
    llm = _Answers()
    profile = _profile("cust_st_cd", glossary=_GLOSSARY)
    described = _described(profile, tmp_path, Overrides(tables={"cust": given}), llm)
    assert llm.prompts == []
    assert described.tables[0].columns[0].reading is None, "the profile holds nothing given"


def test_a_name_read_by_one_candidate_is_read_anew_once_its_term_gains_another(
    tmp_path: Path,
) -> None:
    glossary = {
        "customer": Concept(("cust",)),
        "airplus": Concept(("ap",)),
        "name": Concept(("nm",)),
    }
    profile = _profile("ap_nm", glossary=glossary)
    described = _described(profile, tmp_path / "first")
    assert described.tables[0].columns[0].reading == ("airplus", "name")
    gained = replace(described, glossary={**described.glossary, "contact": Concept(("ap",))})
    llm = _Answers(json.dumps({"1_ap": "contact"}))
    again = _described(gained, tmp_path / "second", llm=llm)
    assert again.tables[0].columns[0].reading == ("contact", "name"), "chosen among both"
    assert len(llm.prompts) == 1
    llm = _Answers()
    _described(again, tmp_path / "third", llm=llm)
    assert llm.prompts == [], "a reading chosen is kept while its terms stay"


def test_a_name_of_a_term_of_no_concept_is_not_asked_for(tmp_path: Path) -> None:
    llm = _Answers()
    described = _described(_profile("cust_st_xy", glossary=_GLOSSARY), tmp_path, llm=llm)
    assert described.tables[0].columns[0].reading is None
    assert all("Some of them may stand" not in prompt for prompt in llm.prompts), (
        "only the concept of xy is asked for"
    )


def test_the_values_shown_to_the_model_are_those_the_profile_may_hold(tmp_path: Path) -> None:
    llm = _Answers()
    samples = {"cust": Sample({"cust_addr": ["DE89370400440532013000", "Hauptstr. 1", "x" * 120]})}
    profile = _profile("cust_addr", glossary={"customer": Concept(("cust",))})
    _described(profile, tmp_path, llm=llm, samples=samples)
    (prompt,) = llm.prompts
    assert f"values: Hauptstr. 1, {'x' * 99}\u2026" in prompt, "no IBAN, and a long one cut"


def test_the_profile_is_written_after_each_table_read(tmp_path: Path) -> None:
    columns = (Column("st_cd", "varchar(10)", Statistics(0, 1)),)
    profile = Profile(
        catalog="crm",
        schema="sales",
        tables=(
            Table(name="cust", rows=1, columns=columns),
            Table(name="ord", rows=1, columns=columns),
        ),
        glossary={**_GLOSSARY, "order": Concept(("ord",))},
    )
    with pytest.raises(LanguageModelError):
        _described(profile, tmp_path, llm=_Failing(json.dumps({"1_st": "street"})))
    cust, ord_ = Profile.read(tmp_path / "profile").tables
    assert cust.columns[0].reading == ("street", "code")
    assert ord_.columns[0].reading is None, "the model failed"
    assert ord_.columns[0].terms is None, "its terms written with its readings alone"


def test_the_abbreviations_no_name_has_any_longer_are_dropped(tmp_path: Path) -> None:
    glossary = {"customer": Concept(("cust", "kd")), "order": Concept(("ord",))}
    described = _described(_profile("cust_nm", glossary=glossary), tmp_path)
    assert described.glossary == {"customer": Concept(("cust",))}, "and a concept of none left"


def test_a_profile_forgotten_has_no_glossary_readings_and_descriptions(tmp_path: Path) -> None:
    llm = _Answers(descriptions=("Who the customer is.",))
    described = _described(_profile("cust_nm", glossary=_GLOSSARY), tmp_path, llm=llm)
    assert described.tables[0].columns[0].description == "Who the customer is."
    profile = forgotten(described)
    assert profile.glossary == {}
    (table,) = profile.tables
    assert table.reading is None
    assert [(c.terms, c.reading, c.description) for c in table.columns] == [
        (described.tables[0].columns[0].terms, None, None)
    ], "its terms as they were split"


def test_the_model_is_told_of_a_column_of_lists_and_its_separator(tmp_path: Path) -> None:
    (table,) = _profile("grp_ids", glossary=_GLOSSARY).tables
    listed = replace(table, columns=(replace(table.columns[0], list_separator=";"),))
    llm = _Answers(descriptions=("The groups.",))
    _described(replace(_profile(glossary=_GLOSSARY), tables=(listed,)), tmp_path, llm=llm)
    (prompt,) = llm.descriptions
    assert '; lists of values separated by ";"' in prompt


def test_the_model_is_told_of_the_types_of_the_values_of_lists(tmp_path: Path) -> None:
    (table,) = _profile("curr_cds", glossary=_GLOSSARY).tables
    items = Findings(Statistics(0, 6), matches=(Match(CURRENCY_CODE, 1.0, 1.0),))
    listed = replace(table, columns=(replace(table.columns[0], list_separator=";", items=items),))
    llm = _Answers(descriptions=("The currencies.",))
    _described(replace(_profile(glossary=_GLOSSARY), tables=(listed,)), tmp_path, llm=llm)
    (prompt,) = llm.descriptions
    assert (
        '; lists of values separated by ";", of 6 distinct values, recognised as currency-code'
        in prompt
    )


def test_a_column_of_no_description_is_described_by_the_model(tmp_path: Path) -> None:
    glossary = {**_GLOSSARY, "customer": Concept(("cust",), "Who buys.")}
    (table,) = _profile("cust_nm", "cust_st_cd", glossary=glossary).tables
    counted = replace(
        table,
        rows=10,
        columns=(
            replace(table.columns[0], statistics=Statistics(2, 8, Lengths(3, 9))),
            replace(table.columns[1], values=(Value("A", 6), Value("B", 4))),
        ),
        column_groups=(ColumnGroup(("cust_nm", "cust_st_cd"), 0.9),),
    )
    profile = replace(_profile(glossary=glossary), tables=(counted,))
    llm = _Answers(json.dumps({"2_st": "status"}), descriptions=(" The name. ", "The status."))
    samples = {"cust": Sample({"cust_nm": ["Anna", "Otto"], "cust_st_cd": ["A", "B"]})}
    described = _described(profile, tmp_path, llm=llm, samples=samples)
    assert [c.description for c in described.tables[0].columns] == ["The name.", "The status."]
    first, second = llm.descriptions
    for fact in (
        "- its name reads: customer_name",
        "- customer: Who buys.",
        "- the name of the table reads: customer",
        "- type: varchar(10); values: Anna, Otto",
        "- rows of the table: 10, of them null: 2, holding a value that stands for none: 0",
        "- distinct values: 8",
        "- lengths: 3 to 9",
        "- the columns beside it: cust_st_cd",
        "- filled in the same rows as: cust_st_cd",
    ):
        assert fact in first, fact
    assert "- its values, with their rows: A (6), B (4)" in second
    assert "- its name reads: customer_status_code" in second, "read by the model before"
    again = _Answers()
    _described(described, tmp_path, llm=again)
    assert again.descriptions == [], "a column described is not asked for again"


def test_the_profile_is_written_after_each_table_described(tmp_path: Path) -> None:
    columns = (Column("cd", "varchar(10)", Statistics(0, 1, range=Range("", "B"))),)
    profile = Profile(
        catalog="crm",
        schema="sales",
        tables=(
            Table(name="cust", rows=1, columns=columns),
            Table(name="ord", rows=1, columns=columns),
        ),
        glossary={**_GLOSSARY, "order": Concept(("ord",))},
    )
    llm = _Failing(json.dumps({"description": "A code."}))
    with pytest.raises(LanguageModelError):
        _described(profile, tmp_path, llm=llm)
    cust, ord_ = Profile.read(tmp_path / "profile").tables
    assert cust.columns[0].description == "A code."
    assert ord_.columns[0].description is None, "the model failed"
    assert "- range: '' to 'B'" in llm.prompts[0], "an empty value is one"


def test_a_description_of_nothing_is_passed_over(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    llm = _Answers(descriptions=("  ",))
    described = _described(_profile("cust_nm", glossary=_GLOSSARY), tmp_path, llm=llm)
    assert described.tables[0].columns[0].description is None
    assert "No description was proposed of the column cust.cust_nm" in caplog.messages


def test_a_column_of_a_description_given_is_not_described_by_the_model(tmp_path: Path) -> None:
    given = TableOverride(columns={"cust_nm": ColumnOverride(description="Given.")})
    llm = _Answers()
    profile = _profile("cust_nm", glossary=_GLOSSARY)
    described = _described(profile, tmp_path, Overrides(tables={"cust": given}), llm)
    assert llm.descriptions == []
    assert described.tables[0].columns[0].description is None, "the profile holds nothing given"


def test_the_names_of_the_example_are_read_from_words_given(
    example_profile: Profile, tmp_path: Path
) -> None:
    glossary = {f"word_{term}": Concept((term,)) for term in occurrences(example_profile)}
    llm = _Answers()
    described = _described(replace(example_profile, glossary=glossary), tmp_path, llm=llm)
    assert llm.prompts == []
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
    overrides = Overrides.read([_EXAMPLE])
    laid = overrides.laid_over(_described(example_profile, tmp_path, overrides))
    glossary = Glossary(laid.glossary)
    columns = {c.name: c for c in laid.tables[1].columns}
    assert laid.tables[1].name == "cust"
    assert glossary.harmonized(columns["ap_ap_nm"]) == "contact_person_name", (
        "a term repeated in two meanings, by the reading given"
    )
    assert glossary.harmonized(columns["cust_ap_id"]) == "contact_person_id", "the name given"
    assert columns["cust_ap_id"].reading == ("customer", "contact_person", "identifier")
    assert glossary.harmonized(columns["ap_seg_cd"]) == "segment_code", "the prefix omitted"
    (iban,) = (c for t in laid.tables for c in t.columns if c.name == "iban")
    assert iban.reading == ("iban",), "by a concept given of its word alone"


def test_a_scan_keeps_the_terms_and_readings_describe_filled(
    source: Source, tmp_path: Path
) -> None:
    workspace = Workspace.open(tmp_path / "workspace", "crm", "sales")
    directory = tmp_path / "profile"
    pattern = re.compile("cust")
    scan(source, pattern, workspace, (), None, Overrides(), directory)
    concepts = {"customer": Concept(("cust",)), "identifier": Concept(("id",))}
    describe(
        Profile.read(directory), Overrides(glossary=concepts), _Answers(), workspace, directory
    )
    described = Profile.read(directory)
    scan(source, pattern, workspace, (), None, Overrides(), directory)
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
    _described(profile, tmp_path, llm=_Answers(_proposal("address")), samples=samples)
    assert "Hauptstr" not in caplog.text
