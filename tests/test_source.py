"""Tests of the source, against the simulation environment, which has to run."""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from data_profiler.profile import Profile
from data_profiler.source import Source, SourceError, connect
from simulation.environment import Environment

_TOP = Path(__file__).parents[1]
_EXAMPLE = Profile.read(_TOP / "simulation" / "profiles" / "crm.yml")
_URL = "trino://profiler@localhost:8443/crm/sales"


@pytest.fixture(scope="session")
def _loaded() -> None:
    """The example profile, loaded into the simulation environment once."""
    with Environment.connect() as environment:
        environment.load(_EXAMPLE)


@pytest.fixture
def _environment(monkeypatch: pytest.MonkeyPatch, _loaded: None) -> None:
    """The environment of a user of the simulation: its certificate trusted, no proxy for it."""
    certificate = _TOP / "simulation" / "trino" / "tls" / "trino.crt"
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(certificate))
    monkeypatch.setenv("NO_PROXY", "localhost")
    monkeypatch.setenv("no_proxy", "localhost")


@pytest.fixture
def source(_environment: None) -> Iterator[Source]:
    """The schema of the example profile, read by its user."""
    with connect(_URL, "profiler") as source:
        yield source


def test_the_tables_that_a_pattern_matches_whole_are_listed(source: Source) -> None:
    assert source.tables(re.compile("cust.*")) == ["cust", "cust_addr"]
    assert source.tables(re.compile("ord|prod")) == ["ord", "prod"]


def test_the_columns_of_a_table_are_listed_with_their_types_in_order(source: Source) -> None:
    columns = source.columns("prod")
    assert list(columns)[:2] == ["prod_id", "prod_cd"]
    assert columns["lst_prc_amt"] == "decimal(10,2)"
    prod = next(table for table in _EXAMPLE.tables if table.name == "prod")
    assert columns == {column.name: column.type for column in prod.columns}


def test_a_query_returns_its_rows(source: Source) -> None:
    assert source.query("SELECT count(*) FROM cust", "counting") == [(5000,)]


def test_a_table_that_does_not_exist_is_named(source: Source) -> None:
    with pytest.raises(SourceError, match=r"^crm\.sales has no table nowhere$"):
        source.columns("nowhere")


def test_a_failing_query_names_the_endpoint_and_the_step(source: Source) -> None:
    with pytest.raises(SourceError) as raised:
        source.query("SELECT * FROM nowhere", "reading nowhere")
    assert str(raised.value) == "Trino at https://localhost:8443 failed reading nowhere"


@pytest.mark.usefixtures("_environment")
def test_a_wrong_password_is_refused_naming_the_user() -> None:
    with (
        connect(_URL, "wrong") as source,
        pytest.raises(SourceError, match="refused the user profiler:"),
    ):
        source.tables(re.compile(".*"))


@pytest.mark.parametrize(
    ("url", "problem"),
    [
        ("postgresql://u:secret@h/c/s", "only a URL of Trino"),
        ("trino://u:secret@h/c/s", "holds a password"),
        ("trino://u@h/c/s?secret=1", "a query or a fragment"),
        ("trino://h/c/s", "lacks user"),
        ("trino://u@h/c", "lacks user"),
        ("trino://u@h//s", "lacks user"),
        ("trino://u@h:x/c/s", "no number from 0 to 65535"),
        ("trino://u@h:70000/c/s", "no number from 0 to 65535"),
    ],
    ids=[
        "another database",
        "a password",
        "a query",
        "no user",
        "no schema",
        "no catalog",
        "a port that is no number",
        "a port out of range",
    ],
)
def test_a_url_that_names_no_schema_of_trino_is_refused_without_repeating_it(
    url: str, problem: str
) -> None:
    with pytest.raises(SourceError, match=problem) as raised:
        connect(url, "")
    assert "secret" not in str(raised.value), "the URL, which may hold a password, is not repeated"


def test_names_are_quoted_in_the_statements_of_the_dialect() -> None:
    with connect(_URL, "") as source:
        statement = source.dialect.columns('c"at', "it's", "t")
    assert '"c""at".information_schema' in statement
    assert "'it''s'" in statement
