"""Tests of the simulation environment, which has to run: profiles loaded and read by Trino."""

from pathlib import Path

import pytest

from data_profiler.profile import Column, Lengths, Profile, Statistics, Table
from simulation import SimulationError
from simulation.environment import Environment

_EXAMPLE = Path(__file__).parents[1] / "profiles" / "crm.yml"


def test_the_example_profile_is_loaded_and_trino_counts_its_rows() -> None:
    profile = Profile.read(_EXAMPLE)
    with Environment.connect() as environment:
        environment.load(profile)
        counted = {
            table.name: environment.count(profile.schema, table.name) for table in profile.tables
        }
    assert counted == {table.name: table.rows for table in profile.tables}


def test_a_profile_of_another_catalog_is_refused() -> None:
    profile = Profile(catalog="billing", schema="sales", tables=())
    with (
        Environment.connect() as environment,
        pytest.raises(SimulationError, match="catalog billing"),
    ):
        environment.load(profile)


def test_a_failure_of_postgresql_names_the_table_but_no_value() -> None:
    column = Column(name="cd", type="varchar(2)", statistics=Statistics(0, 3, Lengths(5, 5)))
    profile = Profile(catalog="crm", schema="tests", tables=(Table("too_long", 3, (column,)),))
    with Environment.connect() as environment, pytest.raises(SimulationError) as raised:
        environment.load(profile)
    assert str(raised.value) == "PostgreSQL at localhost:5432 failed filling tests.too_long"
