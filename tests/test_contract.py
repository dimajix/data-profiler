"""Tests of the data contract: profiles made by hand, written as documents of ODCS.

The contract of the example profile is checked against the JSON schema of ODCS 3.2.0, a copy of
which, of the repository of the standard, `bitol-io/open-data-contract-standard`, lies in
`tests/odcs/` with its license, the Apache License 2.0.
"""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator
from yaml import safe_load

from data_profiler.contract import Contract
from data_profiler.detect import (
    COUNTRY_NUMBER,
    CURRENCY_NUMBER,
    IBAN,
    POSTAL_CODE,
    SENTINELS,
    TRUE_FALSE,
    UUID,
    Sensitivity,
)
from data_profiler.overrides import ColumnOverride, Overrides, TableOverride
from data_profiler.profile import (
    Column,
    Concept,
    Findings,
    Lengths,
    Match,
    PrimaryKey,
    Profile,
    Range,
    Reference,
    Statistics,
    Table,
    Term,
    Value,
)
from data_profiler.project import ContractSettings
from data_profiler.source import dialect, locate

_TOP = Path(__file__).parents[1]
_SCHEMA = Path(__file__).parent / "odcs" / "odcs-json-schema-v3.2.0.json"
_URL = "trino://starburst.example.com:8443/crm/sales"
_SETTINGS = ContractSettings(id="crm-sales", version="1.0.0")


def _contract(
    profile: Profile,
    overrides: Overrides | None = None,
    settings: ContractSettings = _SETTINGS,
) -> Any:
    """The contract of `profile`, `overrides` laid over it as `Template.write` lays them."""
    given = overrides or Overrides()
    template = Contract(settings, "prod", locate(_URL), dialect(_URL))
    (content,) = template.files(given.laid_over(profile), given).values()
    return safe_load(content)


def _profile(*columns: Column, **table: Any) -> Profile:
    """A profile of one table, `ord`, of 100 rows, of `columns` and what `table` gives of it."""
    return Profile("crm", "sales", tables=(Table("ord", 100, columns, **table),))


def _column(name: str = "ord_no", kind: str = "varchar(14)", **found: Any) -> Column:
    """A column of no nulls and 100 distinct values, of what `found` gives of it."""
    return Column(name, kind, found.pop("statistics", Statistics(0, 100)), **found)


def _property(contract: Any, name: str) -> Any:
    """The property `name` of the first schema object of `contract`."""
    (found,) = (each for each in contract["schema"][0]["properties"] if each["name"] == name)
    return found


def test_the_contract_of_the_example_profile_is_valid_against_the_schema_of_odcs(
    example_profile: Profile,
) -> None:
    overrides = Overrides.read([_TOP / "examples" / "crm" / "overrides.yml"])
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft201909Validator(schema).iter_errors(_contract(example_profile, overrides)))
    assert not errors, [error.message for error in errors]


def test_a_contract_holds_what_the_project_gives_of_it_and_is_a_draft() -> None:
    settings = ContractSettings("crm-sales", "1.2.0", "CRM sales", "sales", "wholesale")
    contract = _contract(_profile(_column()), settings=settings)
    assert {key: contract[key] for key in list(contract)[:8]} == {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "crm-sales",
        "version": "1.2.0",
        "status": "draft",
        "name": "CRM sales",
        "domain": "sales",
        "tenant": "wholesale",
    }


def test_a_contract_leaves_out_what_is_not_given_of_it() -> None:
    contract = _contract(_profile(_column()))
    assert not {"name", "domain", "tenant", "description"} & contract.keys()


def test_the_purpose_of_a_contract_is_the_description_of_the_database_given() -> None:
    contract = _contract(_profile(_column()), Overrides(description="The CRM."))
    assert contract["description"] == {"purpose": "The CRM."}


def test_the_server_of_a_contract_is_that_of_the_environment() -> None:
    assert _contract(_profile(_column()))["servers"] == [
        {
            "server": "prod",
            "type": "trino",
            "host": "starburst.example.com",
            "port": 8443,
            "catalog": "crm",
            "schema": "sales",
        }
    ]


def test_a_table_and_a_column_are_named_by_their_original_names_and_their_harmonized_ones() -> None:
    terms = (Term("ord", ("order",)), Term("no", ("number",)))
    column = replace(_column(), terms=terms, reading=("order", "number"))
    table = Table("ord", 100, (column,), terms=(Term("ord", ("order",)),), reading=("order",))
    profile = Profile(
        "crm",
        "sales",
        tables=(table,),
        glossary={"order": Concept(("ord",)), "number": Concept(("no",))},
    )
    overrides = Overrides(
        tables={"ord": TableOverride(columns={"ord_no": ColumnOverride(description="It.")})}
    )
    (found,) = _contract(profile, overrides)["schema"]
    assert {key: found[key] for key in list(found)[:5]} == {
        "name": "ord",
        "physicalName": "ord",
        "physicalType": "table",
        "logicalType": "object",
        "businessName": "order",
    }
    assert {key: found["properties"][0][key] for key in list(found["properties"][0])[:6]} == {
        "name": "ord_no",
        "physicalName": "ord_no",
        "businessName": "order_number",
        "description": "It.",
        "logicalType": "string",
        "physicalType": "varchar(14)",
    }


def test_a_column_of_no_nulls_and_no_sentinels_is_required_and_holds_none_of_the_sentinels() -> (
    None
):
    found = _property(_contract(_profile(_column())), "ord_no")
    assert found["required"] is True
    (missing,) = found["quality"]
    assert missing["metric"] == "missingValues"
    assert missing["mustBe"] == 0
    assert {"", "N/A", "-"} <= set(missing["arguments"]["missingValues"])


def test_the_sentinels_given_of_a_column_are_the_missing_values_of_its_rule() -> None:
    column = _column(sentinels=("00000",))
    (missing,) = _property(_contract(_profile(column)), "ord_no")["quality"]
    assert missing["arguments"] == {"missingValues": ["00000"]}


def test_a_column_of_nulls_or_of_sentinels_found_is_neither_required_nor_without_sentinels() -> (
    None
):
    nulls = _column("a", statistics=Statistics(3, 97))
    found = _column("b", statistics=Statistics(0, 97, sentinels=(Value("-", 3),)))
    contract = _contract(_profile(nulls, found))
    assert "required" not in _property(contract, "a")
    assert "quality" not in _property(contract, "a")
    assert _property(contract, "b")["required"] is True
    assert "quality" not in _property(contract, "b")


def test_a_rule_of_sentinels_holds_those_that_are_values_of_the_type_of_its_column() -> None:
    nil = "00000000-0000-0000-0000-000000000000"
    number = _column("nr", "bigint")
    key = _column("ref", "uuid")
    day = _column("dt", "date")
    moment = _column("at", "timestamp(3)")
    nothing = _column("no", "uuid", sentinels=(nil, "N/A"))
    document = _column("doc", "json")
    contract = _contract(_profile(number, key, day, moment, nothing, document))
    assert "quality" not in _property(contract, "nr"), "a number holds none of the tool's"
    assert "quality" not in _property(contract, "ref"), "nor does a UUID"
    for name in ("dt", "at"):
        (missing,) = _property(contract, name)["quality"]
        assert missing["arguments"]["missingValues"] == ["0001-01-01", "1900-01-01", "9999-12-31"]
    (missing,) = _property(contract, "no")["quality"]
    assert missing["arguments"]["missingValues"] == [nil], "a UUID given that it can hold"
    (missing,) = _property(contract, "doc")["quality"]
    assert missing["arguments"]["missingValues"] == sorted(SENTINELS), "JSON, all as texts"


def test_a_column_the_database_writes_as_no_text_has_no_rule_of_sentinels() -> None:
    found = _property(_contract(_profile(_column("tags", "array(varchar)"))), "tags")
    assert found["logicalType"] == "array"
    assert "quality" not in found


def test_the_keys_of_a_table_are_unique_and_its_primary_key_named_by_its_positions() -> None:
    profile = _profile(
        _column("ord_id", "bigint"),
        _column("pos_no", "integer"),
        _column("ord_no"),
        keys=(("ord_no",), ("ord_id", "pos_no")),
        primary_key=PrimaryKey(("ord_id", "pos_no")),
    )
    contract = _contract(profile)
    assert _property(contract, "ord_no")["unique"] is True
    assert "unique" not in _property(contract, "ord_id")
    assert [_property(contract, name).get("primaryKey") for name in ("ord_id", "ord_no")] == [
        True,
        None,
    ]
    assert [
        _property(contract, name).get("primaryKeyPosition") for name in ("ord_id", "pos_no")
    ] == [
        1,
        2,
    ]
    assert contract["schema"][0]["quality"] == [
        {
            "metric": "duplicateValues",
            "arguments": {"properties": ["ord_id", "pos_no"]},
            "mustBe": 0,
        }
    ]


def test_a_reference_is_a_relationship_to_its_key_without_its_coverage() -> None:
    profile = _profile(
        _column("cust_id", "bigint"), references=(Reference("cust_id", "cust", "id", 0.98),)
    )
    assert _property(_contract(profile), "cust_id")["relationships"] == [{"to": "cust.id"}]


def test_a_reference_candidate_and_the_reference_of_a_column_of_lists_are_no_relationships() -> (
    None
):
    items = Findings(Statistics(0, 30))
    profile = _profile(
        _column("cust_no", "bigint"),
        _column("prod_ids", list_separator=";", items=items),
        references=(Reference("prod_ids", "prod", "prod_id", 0.99),),
        reference_candidates=(Reference("cust_no", "cust", "id", 0.95),),
    )
    contract = _contract(profile)
    assert "relationships" not in _property(contract, "cust_no")
    assert "relationships" not in _property(contract, "prod_ids")


def test_a_column_is_classified_by_its_sensitivity_and_tagged_by_its_semantic_types() -> None:
    iban = _column("iban", matches=(Match(IBAN, 1.0, 0.9),))
    numbers = _column(
        "nr", "integer", matches=(Match(COUNTRY_NUMBER, 1.0, 1.0), Match(CURRENCY_NUMBER, 1.0, 1.0))
    )
    contract = _contract(_profile(iban, numbers, _column("plain", marked=Sensitivity.NONE)))
    assert _property(contract, "iban")["classification"] == "personal"
    assert _property(contract, "iban")["tags"] == ["iban"]
    assert "classification" not in _property(contract, "plain")
    assert _property(contract, "nr")["tags"] == ["country-number", "currency-number"]


def test_a_semantic_type_every_value_of_the_table_is_of_gives_a_rule_of_its_pattern() -> None:
    full = _column("a", statistics=Statistics(1, 99), matches=(Match(IBAN, 1.0, 1.0),))
    part = _column("b", statistics=Statistics(1, 99), matches=(Match(IBAN, 1.0, 0.9),))
    contract = _contract(_profile(full, part))
    (invalid,) = _property(contract, "a")["quality"]
    assert invalid["metric"] == "invalidValues"
    assert invalid["arguments"]["pattern"] == rf"^\s*(?:{IBAN.detector.pattern.pattern})\s*$"
    assert invalid["mustBe"] == 0
    assert "quality" not in _property(contract, "b")


def test_a_column_of_another_type_than_texts_has_no_rule_of_a_pattern() -> None:
    flags = _column("flg", "boolean", matches=(Match(TRUE_FALSE, 1.0, 1.0),))
    assert "quality" not in _property(_contract(_profile(flags)), "flg")


def test_a_column_of_uuids_is_of_the_format_uuid() -> None:
    column = _column("ref", "varchar(36)", matches=(Match(UUID, 1.0, 1.0),))
    assert _property(_contract(_profile(column)), "ref")["logicalTypeOptions"]["format"] == "uuid"


def test_the_values_of_an_enumeration_are_those_a_column_takes_as_its_type_writes_them() -> None:
    codes = _column("sts", "varchar(3)", values=(Value("NEW", 60), Value("OK", 40)))
    numbers = _column("prio", "integer", values=(Value("1", 60), Value("2", 40)))
    contract = _contract(_profile(codes, numbers))
    assert _property(contract, "sts")["enum"] == [{"value": "NEW"}, {"value": "OK"}]
    assert _property(contract, "prio")["enum"] == [{"value": 1}, {"value": 2}]


def test_the_lengths_and_the_range_of_a_column_are_the_bounds_of_its_values() -> None:
    text = _column(statistics=Statistics(0, 100, Lengths(14, 14), Range("A", "Z")))
    amount = _column(
        "amt", "decimal(14,2)", statistics=Statistics(0, 100, range=Range("0.5", "99"))
    )
    day = _column("dt", "date", statistics=Statistics(0, 100, range=Range("2024-01-01", None)))
    large = Range("12345678901234567890", "12345678901234567891")
    whole = _column("big", "decimal(20,0)", statistics=Statistics(0, 100, range=large))
    contract = _contract(_profile(text, amount, whole, day))
    assert _property(contract, "ord_no")["logicalTypeOptions"] == {"minLength": 14, "maxLength": 14}
    assert _property(contract, "amt")["logicalTypeOptions"] == {"minimum": 0.5, "maximum": 99}
    assert _property(contract, "big")["logicalTypeOptions"] == {
        "minimum": 12345678901234567890,
        "maximum": 12345678901234567891,
    }, "a whole number keeps its digits"
    assert _property(contract, "dt")["logicalTypeOptions"] == {"minimum": "2024-01-01"}


def test_the_rules_of_the_values_of_a_column_take_the_sentinels_found_as_values() -> None:
    found = (Value("", 40), Value("01.01.1900", 2))
    code = _column(
        "cd",
        "varchar(10)",
        statistics=Statistics(0, 2, Lengths(5, 5), sentinels=found),
        matches=(Match(POSTAL_CODE, 1.0, 1.0),),
        values=(Value("12345", 50), Value("54321", 8)),
    )
    day = _column(
        "dt",
        "date",
        statistics=Statistics(
            0, 9, range=Range("2024-01-01", "2024-12-31"), sentinels=(Value("9999-12-31", 3),)
        ),
    )
    key = _column("ref", "varchar(36)", statistics=Statistics(0, 9, sentinels=found[:1]))
    key = replace(key, matches=(Match(UUID, 1.0, 1.0),))
    contract = _contract(_profile(code, day, key))
    found_code = _property(contract, "cd")
    assert [each["value"] for each in found_code["enum"]] == ["12345", "54321", "", "01.01.1900"]
    assert found_code["logicalTypeOptions"] == {"minLength": 0, "maxLength": 10}
    (invalid,) = found_code["quality"]
    pattern = POSTAL_CODE.detector.pattern.pattern
    assert invalid["arguments"]["pattern"] == rf"^\s*(?:{pattern}||01\.01\.1900)\s*$"
    assert _property(contract, "dt")["logicalTypeOptions"] == {
        "minimum": "2024-01-01",
        "maximum": "9999-12-31",
    }
    assert "format" not in _property(contract, "ref").get("logicalTypeOptions", {})


def test_a_contract_holds_nothing_counted() -> None:
    contract = _contract(_profile(_column(), references=(Reference("ord_no", "x", "y", 0.5),)))
    text = json.dumps(contract)
    assert "rowCount" not in text
    assert "coverage" not in text
    assert "0.5" not in text
