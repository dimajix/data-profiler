"""Tests of the source, against the simulation environment, which has to run."""

import re

import pytest

from data_profiler.profile import Profile
from data_profiler.source import Source, SourceError, connect


def test_the_tables_that_a_pattern_matches_whole_are_listed(source: Source) -> None:
    assert source.tables(re.compile("cust.*")) == ["cust", "cust_addr"]
    assert source.tables(re.compile("ord|prod")) == ["ord", "prod"]


def test_the_columns_of_a_table_are_listed_with_their_types_in_order(
    source: Source, example: Profile
) -> None:
    columns = source.columns("prod")
    assert list(columns)[:2] == ["prod_id", "prod_cd"]
    assert columns["lst_prc_amt"] == "decimal(10,2)"
    prod = next(table for table in example.tables if table.name == "prod")
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


@pytest.mark.usefixtures("user_environment")
def test_a_wrong_password_is_refused_naming_the_user(url: str) -> None:
    with (
        connect(url, "wrong") as source,
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
    with connect("trino://u@h/c/s", "") as source:
        columns = source.dialect.columns('c"at', "it's", "t")
        select = source.dialect.select([source.dialect.longest('c"y')], 't"x')
        sampled = source.dialect.sampled([source.dialect.column('c"y')], 't"x', 1.5, 10)
        grouped = source.dialect.grouped([source.dialect.grouping('c"y')], 't"x', ['c"y'])
        matching = source.dialect.matching('c"y', "it's")
    assert '"c""at".information_schema' in columns
    assert "'it''s'" in columns
    assert 'length("c""y")' in select
    assert select.endswith('FROM "t""x"')
    assert sampled.startswith('SELECT "c""y" FROM "t""x" TABLESAMPLE')
    assert grouped.startswith('SELECT grouping("c""y") FROM "t""x" GROUP BY')
    assert grouped.endswith('(("c""y"))')
    assert 'try_cast("c""y" AS varchar)' in matching
    assert "'^(?:it''s)$'" in matching
