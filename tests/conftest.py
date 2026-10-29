"""The fixtures of the tests that read the simulation environment, which has to run."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from data_profiler.profile import Profile
from data_profiler.source import Source, connect
from simulation.environment import Environment

_TOP = Path(__file__).parents[1]


@pytest.fixture(scope="session")
def example() -> Profile:
    """The example profile of the simulation, loaded into its environment once."""
    profile = Profile.read(_TOP / "simulation" / "profiles" / "crm.yml")
    with Environment.connect() as environment:
        environment.load(profile)
    return profile


@pytest.fixture
def user_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The environment of a user of the simulation: its certificate trusted, no proxy for it."""
    certificate = _TOP / "simulation" / "trino" / "tls" / "trino.crt"
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(certificate))
    monkeypatch.setenv("NO_PROXY", "localhost")
    monkeypatch.setenv("no_proxy", "localhost")


@pytest.fixture(scope="session")
def url(example: Profile) -> str:
    """The URL of the schema of the example profile, as the user of the simulation reads it."""
    return f"trino://profiler@localhost:8443/{example.catalog}/{example.schema}"


@pytest.fixture
def source(user_environment: None, url: str) -> Iterator[Source]:
    """The schema of the example profile, read by the user of the simulation."""
    with connect(url, "profiler") as source:
        yield source
