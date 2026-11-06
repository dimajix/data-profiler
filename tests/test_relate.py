"""Tests of the stage relate, which writes the references of a profile; some need the simulation."""

from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.overrides import (
    ColumnOverride,
    Overrides,
    OverridesError,
    ReferenceOverride,
    TableOverride,
)
from data_profiler.profile import Profile, ProfileError
from data_profiler.relate import relate
from data_profiler.source import Source, connect

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm" / "overrides.yml"


def _unrelated(profile: Profile) -> Profile:
    """`profile`, of no references."""
    return replace(profile, tables=tuple(replace(t, references=()) for t in profile.tables))


def test_the_profile_is_written_with_the_references_of_its_tables(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    _unrelated(example).write(tmp_path)
    relate(source, Overrides(), tmp_path)
    related = Profile.read(tmp_path).table("ord")
    assert [r.column for r in related.references] == ["cntct_uuid", "dlvr_addr_guid"]


def test_a_profile_of_another_schema_is_refused_before_anything_is_queried(
    example: Profile, tmp_path: Path
) -> None:
    replace(_unrelated(example), schema="billing").write(tmp_path)
    with (
        connect("trino://h/crm/sales", "u", "") as source,
        pytest.raises(ProfileError, match=r"is of crm\.billing, not of crm\.sales"),
    ):
        relate(source, Overrides(), tmp_path)


def test_the_references_the_overrides_give_are_taken_as_given(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    _unrelated(example).write(tmp_path)
    relate(source, Overrides.read(_EXAMPLE), tmp_path)
    related = Profile.read(tmp_path)
    (cust_id,) = [r for r in related.table("ord").references if r.column == "cust_id"]
    assert (cust_id.table, cust_id.given) == ("cust", True)
    assert not [c for c in related.table("ord").candidates if c.column == "cust_id"], "not searched"


def test_a_reference_given_to_what_is_not_profiled_is_refused_before_anything_is_queried(
    example: Profile, tmp_path: Path
) -> None:
    _unrelated(example).write(tmp_path)
    reference = ColumnOverride(reference=ReferenceOverride("prod", "prod_no"))
    overrides = Overrides(tables={"ord": TableOverride(columns={"cust_id": reference})})
    with (
        connect("trino://h/crm/sales", "u", "") as source,
        pytest.raises(OverridesError, match="which prod does not have"),
    ):
        relate(source, overrides, tmp_path)
