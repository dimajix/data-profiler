"""Tests of the source, against the simulation environment, which has to run."""

import re

import pytest

from data_profiler.profile import Profile
from data_profiler.source import Lookup, Probe, Source, SourceError, connect


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
        connect(url, "profiler", "wrong") as source,
        pytest.raises(SourceError, match="refused the user profiler:"),
    ):
        source.tables(re.compile(".*"))


@pytest.mark.parametrize(
    ("url", "problem"),
    [
        ("postgresql://u:secret@h/c/s", "only a URL of Trino"),
        ("trino://u:secret@h/c/s", "holds a user or a password"),
        ("trino://:secret@h/c/s", "holds a user or a password"),
        ("trino://u@h/c/s", "holds a user or a password"),
        ("trino://h/c/s?secret=1", "a query or a fragment"),
        ("trino:///c/s", "lacks host"),
        ("trino://h/c", "lacks host"),
        ("trino://h//s", "lacks host"),
        ("trino://h:x/c/s", "no number from 0 to 65535"),
        ("trino://h:70000/c/s", "no number from 0 to 65535"),
    ],
    ids=[
        "another database",
        "a password",
        "a password without a user",
        "a user",
        "a query",
        "no host",
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
        connect(url, "u", "")
    assert "secret" not in str(raised.value), "the URL, which may hold a password, is not repeated"


def test_a_schema_is_not_read_as_an_empty_user() -> None:
    with pytest.raises(SourceError, match="the user to read the schema as is empty"):
        connect("trino://h/c/s", "", "")


def test_names_are_quoted_in_the_statements_of_the_dialect() -> None:
    with connect("trino://h/c/s", "u", "") as source:
        columns = source.dialect.columns('c"at', "it's", "t")
        values = source.dialect.column('c"y')
        select = source.dialect.select([source.dialect.longest(values)], 't"x')
        sampled = source.dialect.sampled([values], 't"x', 1.5, 10)
        grouped = source.dialect.grouped([source.dialect.grouping('c"y')], 't"x', ['c"y'])
        matching = source.dialect.matching(values, "it's")
        ranged = [source.dialect.smallest(values), source.dialect.largest(values)]
        without = source.dialect.without('c"y', "varchar(3)", {"it's"})
        moments = source.dialect.sentinels('c"y', "timestamp(3)", {"9999-12-31", ""})
        distinct = [
            source.dialect.exactly_distinct(['c"y']),
            source.dialect.exactly_distinct(['c"y', "z"]),
        ]
    assert '"c""at".information_schema' in columns
    assert "'it''s'" in columns
    assert 'length("c""y")' in select
    assert select.endswith('FROM "t""x"')
    assert sampled.startswith('SELECT "c""y" FROM "t""x" TABLESAMPLE')
    assert grouped.startswith('SELECT grouping("c""y") FROM "t""x" GROUP BY')
    assert grouped.endswith('(("c""y"))')
    assert 'try_cast("c""y" AS varchar)' in matching
    assert "'^(?:it''s)$'" in matching
    assert ranged == ['min("c""y")', 'max("c""y")']
    assert without.endswith('ELSE "c""y" END')
    assert "IN ('it''s')" in without
    assert 'CAST("c""y" AS date)' in moments, "a moment compared as its day"
    assert "IN ('', '9999-12-31')" in moments
    assert distinct == ['count(DISTINCT "c""y")', 'count(DISTINCT ROW("c""y", "z"))']


def test_the_distinct_values_of_columns_together_are_counted_exactly(source: Source) -> None:
    dialect = source.dialect
    sets = [("ord_itm_id",), ("pos_no",), ("ord_id", "pos_no")]
    statement = dialect.select([dialect.rows(), *map(dialect.exactly_distinct, sets)], "ord_itm")
    assert source.query(statement, "counting the distinct values") == [(61000, 61000, 9, 61000)]


def test_names_are_quoted_in_the_statements_of_the_references() -> None:
    with connect("trino://h/c/s", "u", "") as source:
        values = source.dialect.column('c"y')
        probed = source.dialect.probed([Probe('t"x', values, 2.5)], [('k"t', 'k"y')], 100)
        covered = source.dialect.covered('t"x', [Lookup(values, 'k"t', 'k"y')])
    assert 'CAST("c""y" AS varchar) AS "v" FROM "t""x" TABLESAMPLE BERNOULLI' in probed
    assert 'CAST("k""y" AS varchar) AS "id" FROM "k""t"' in probed
    assert 'CAST("c""y" AS varchar) AS "v0" FROM "t""x"' in covered
    assert 'CAST("k""y" AS varchar) AS "id" FROM "k""t"' in covered


def test_the_values_of_probes_found_in_keys_are_counted_of_those_taken(source: Source) -> None:
    dialect = source.dialect
    probes = [
        Probe("ord", dialect.column("cust_id"), 10.0),
        Probe("ord_itm", dialect.column("qty"), 1.0),
    ]
    keys = [("cust", "cust_id"), ("prod", "prod_id")]
    rows = source.query(dialect.probed(probes, keys, 100), "probing")
    found = {(probe, key): (taken, matched) for probe, key, taken, matched in rows}
    (taken, matched) = found[0, 0]
    assert taken == 100
    assert isinstance(matched, int)
    assert 90 <= matched <= 100, "98 of 100 orders refer to a customer"
    assert (0, 1) not in found, "no customer is a product"
    assert found[1, 0] == (100, 100), "a quantity is the number of a customer, by chance"


def test_the_values_of_a_table_found_in_keys_are_counted_on_the_whole_table(source: Source) -> None:
    dialect = source.dialect
    cust = dialect.column("cust_id")
    lookups = [Lookup(cust, "cust", "cust_id"), Lookup(cust, "prod", "prod_id")]
    statement = dialect.covered("ord", lookups)
    assert source.query(statement, "counting") == [(20000, 19600, 20000, 0)]


@pytest.mark.parametrize(
    ("kind", "other", "compared"),
    [
        ("bigint", "integer", True),
        ("bigint", "decimal(12,0)", True),
        ("decimal(12,2)", "decimal(10,2)", True),
        ("decimal(12,2)", "decimal(12,3)", False),
        ("varchar(12)", "char(12)", True),
        ("varchar(12)", "bigint", False),
        ("date", "date", True),
        ("date", "timestamp(3)", False),
        ("uuid", "uuid", True),
    ],
)
def test_values_of_types_of_one_family_are_compared_as_text(
    kind: str, other: str, compared: bool
) -> None:
    with connect("trino://h/c/s", "u", "") as source:
        assert source.dialect.is_same_family(kind, other) == compared


@pytest.mark.parametrize(("kind", "unmistakable"), [("uuid", True), ("varchar(36)", False)])
def test_only_uuids_are_unmistakable_by_their_type(kind: str, unmistakable: bool) -> None:
    with connect("trino://h/c/s", "u", "") as source:
        assert source.dialect.is_unmistakable(kind) == unmistakable


def test_a_column_without_sentinels_is_counted_as_it_is() -> None:
    with connect("trino://h/c/s", "u", "") as source:
        assert source.dialect.without("c", "array(integer)", ()) == '"c"'


@pytest.mark.parametrize(
    ("kind", "written"),
    [("varchar(40)", True), ("json", True), ("array(integer)", False), ("varbinary", False)],
)
def test_only_the_types_the_database_casts_to_a_text_have_text(kind: str, written: bool) -> None:
    with connect("trino://h/c/s", "u", "") as source:
        assert source.dialect.has_text(kind) == written


@pytest.mark.parametrize(
    ("kind", "ordered"),
    [
        ("varchar(40)", True),
        ("decimal(12,2)", True),
        ("timestamp(3) with time zone", True),
        ("boolean", True),
        ("json", False),
        ("map(varchar, integer)", False),
        ("array(integer)", False),
        ("varbinary", False),
    ],
)
def test_only_the_types_whose_values_have_an_order_are_ordered(kind: str, ordered: bool) -> None:
    with connect("trino://h/c/s", "u", "") as source:
        assert source.dialect.is_ordered(kind) == ordered


@pytest.mark.parametrize(
    ("kind", "identifies", "surrogate"),
    [
        ("bigint", True, True),
        ("uuid", True, True),
        ("decimal(12,0)", True, True),
        ("decimal(12,2)", True, False),
        ("varchar(12)", True, False),
        ("char(3)", True, False),
        ("date", True, False),
        ("double", False, False),
        ("real", False, False),
        ("timestamp(3)", False, False),
        ("time(3)", False, False),
        ("boolean", False, False),
        ("varbinary", False, False),
        ("array(integer)", False, False),
    ],
)
def test_only_the_types_of_exact_values_identify_rows(
    kind: str, identifies: bool, surrogate: bool
) -> None:
    with connect("trino://h/c/s", "u", "") as source:
        assert source.dialect.identifies(kind) == identifies
        assert source.dialect.is_surrogate(kind) == surrogate, "a key a database generates"


@pytest.mark.parametrize(
    "kind",
    [
        "tinyint",
        "smallint",
        "integer",
        "bigint",
        "real",
        "double",
        "decimal(10,2)",
        "varchar(5)",
        "char(3)",
        "date",
        "time(3)",
        "timestamp(3)",
        "timestamp(3) with time zone",
        "interval day to second",
        "interval year to month",
        "boolean",
        "uuid",
    ],
)
def test_the_database_has_a_range_of_every_type_the_dialect_takes_as_ordered(
    source: Source, kind: str
) -> None:
    assert source.dialect.is_ordered(kind)
    # The statement is the test's own: a column of each type is had of no table of the simulation.
    statement = f"SELECT min(CAST(NULL AS {kind})), max(CAST(NULL AS {kind}))"
    assert source.query(statement, f"ordering {kind}") == [(None, None)]
