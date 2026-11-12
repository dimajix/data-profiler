"""Tests of the source, against the simulation environment, which has to run."""

import re
from collections.abc import Collection
from datetime import date

import pytest

from data_profiler.detect import SENTINELS
from data_profiler.profile import Profile
from data_profiler.source import (
    Location,
    Lookup,
    Probe,
    Source,
    SourceError,
    connect,
    dialect,
    locate,
)


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
        locate(url)
    assert "secret" not in str(raised.value), "the URL, which may hold a password, is not repeated"


def test_a_url_is_located_by_its_host_port_catalog_and_schema() -> None:
    assert locate("trino://h:8443/c/s") == Location("h", 8443, "c", "s")
    assert locate("trino://h/c/s").port == 443, "that of HTTPS, where the URL names none"


def test_a_url_that_names_no_schema_is_refused_by_connect_and_dialect_as_by_locate() -> None:
    with pytest.raises(SourceError, match="only a URL of Trino is read"):
        connect("postgresql://h/c/s", "u", "")
    with pytest.raises(SourceError, match="only a URL of Trino is read"):
        dialect("postgresql://h/c/s")


def test_the_dialect_of_a_url_is_known_without_connecting() -> None:
    assert dialect("trino://nowhere.invalid/c/s").server_type == "trino"


@pytest.mark.parametrize(
    ("kind", "logical"),
    [
        ("varchar(14)", "string"),
        ("char(2)", "string"),
        ("uuid", "string"),
        ("bigint", "integer"),
        ("decimal(14,2)", "number"),
        ("double", "number"),
        ("boolean", "boolean"),
        ("date", "date"),
        ("timestamp(3) with time zone", "timestamp"),
        ("time(3)", "time"),
        ("array(varchar)", "array"),
        ("map(varchar, bigint)", None),
        ("json", None),
    ],
)
def test_the_logical_type_of_a_type_of_trino_is_that_of_odcs(
    kind: str, logical: str | None
) -> None:
    assert dialect("trino://h/c/s").logical_type(kind) == logical


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
        matching = source.dialect.matching(values, "varchar(3)", "it's")
        ranged = [source.dialect.smallest(values), source.dialect.largest(values)]
        without = source.dialect.without('c"y', "varchar(3)", {"it's"})
        moments = source.dialect.sentinels('c"y', "timestamp(3)", {"9999-12-31", ""})
        distinct = [
            source.dialect.exactly_distinct([values]),
            source.dialect.exactly_distinct([values, source.dialect.column("z")]),
        ]
        unnested = source.dialect.unnested('t"x', ['c"y', "z"], 'c"y', "'").select(["1"], 't"x')
    assert '"c""at".information_schema' in columns
    assert "'it''s'" in columns
    assert 'length("c""y")' in select
    assert select.endswith('FROM "t""x"')
    assert unnested == (
        'SELECT 1 FROM (SELECT "u"."v" AS "c""y", "t"."z" FROM "t""x" "t"'
        ' CROSS JOIN UNNEST(split("t"."c""y", \'\'\'\')) AS "u" ("v"))'
    ), "the values of the lists under the name of their column, the others as they are"
    assert sampled.startswith('SELECT "c""y" FROM "t""x" TABLESAMPLE')
    assert grouped.startswith('SELECT grouping("c""y") FROM "t""x" GROUP BY')
    assert grouped.endswith('(("c""y"))')
    assert 'CAST("c""y" AS varchar)' in matching
    assert "'^(?:it''s)$'" in matching
    assert ranged == ['min("c""y")', 'max("c""y")']
    assert without.endswith('ELSE "c""y" END')
    assert "IN ('it''s')" in without
    assert 'CAST("c""y" AS date)' in moments, "a moment compared as its day"
    assert "IN ('', '9999-12-31')" in moments
    assert distinct == [
        'count(DISTINCT "c""y")',
        'count(DISTINCT CASE WHEN "c""y" IS NOT NULL THEN ROW("c""y", "z") END)',
    ]


def test_the_distinct_values_of_columns_together_are_counted_exactly(source: Source) -> None:
    dialect = source.dialect
    sets = [("ord_itm_id",), ("pos_no",), ("ord_id", "pos_no")]
    counts = (dialect.exactly_distinct([dialect.column(name) for name in found]) for found in sets)
    statement = dialect.select([dialect.rows(), *counts], "ord_itm")
    assert source.query(statement, "counting the distinct values") == [(61000, 61000, 9, 61000)]


def test_the_counts_of_a_table_are_counted_in_queries_of_ten_at_most_in_their_order(
    source: Source, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[str] = []
    query = source.query

    def sending(statement: str, step: str) -> list[tuple[object, ...]]:
        sent.append(statement)
        return query(statement, step)

    monkeypatch.setattr(source, "query", sending)
    dialect = source.dialect
    counts = [dialect.rows(), dialect.exactly_distinct([dialect.column("pos_no")])] * 6
    assert source.counts("ord_itm", counts, "counting") == [61000, 9] * 6
    assert len(sent) == 2


def test_distinct_values_are_counted_where_the_first_is_not_null_the_nulls_of_others_values(
    source: Source,
) -> None:
    dialect = source.dialect
    city, customer = dialect.column("dlvr_cty_nm"), dialect.column("cust_id")
    counts = [
        dialect.exactly_distinct([city, customer]),
        dialect.exactly_distinct([customer, city]),
    ]
    (found,) = source.query(dialect.select(counts, "ord"), "counting the distinct values")
    pairs = 'SELECT count(*) FROM (SELECT DISTINCT "dlvr_cty_nm", "cust_id" FROM "ord"'
    of_cities = f'{pairs} WHERE "dlvr_cty_nm" IS NOT NULL)'
    ((cities,),) = source.query(of_cities, "counting the pairs of a city")
    ((all_pairs,),) = source.query(f"{pairs})", "counting all pairs")
    assert found == (cities, all_pairs), "the nulls of the cities a value of the customers"
    assert cities != all_pairs, "the delivery addresses of the simulation hold nulls"


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


_DAYS = {"0001-01-01", "1900-01-01", "9999-12-31"}
_NIL = "00000000-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    ("kind", "texts", "held"),
    [
        ("varchar(40)", SENTINELS, SENTINELS),
        ("char(3)", SENTINELS, SENTINELS),
        ("json", SENTINELS, SENTINELS),
        ("array(integer)", {"", "-1"}, set()),
        ("varbinary", {"", "-1"}, set()),
        ("bigint", SENTINELS | {"-1", "0", "1.0", "1.0E0"}, {"-1", "0"}),
        ("decimal(12,0)", {"-1", "-1.00"}, {"-1"}),
        ("decimal(12,2)", {"-1", "-1.00", "0.5", "0.50"}, {"-1.00", "0.50"}),
        (
            "double",
            SENTINELS | {"-1", "-1.0E0", "1.5E-10", "NaN", "-Infinity"},
            {"-1.0E0", "1.5E-10", "NaN", "-Infinity"},
        ),
        ("real", {"0", "0E0", "-1.234568E7"}, {"0E0", "-1.234568E7"}),
        ("date", SENTINELS, _DAYS),
        ("timestamp(3)", SENTINELS, _DAYS),
        ("timestamp(3) with time zone", SENTINELS, _DAYS),
        ("time(3)", SENTINELS | {"00:00:00.000", "00:00"}, {"00:00:00.000"}),
        ("time(3) with time zone", {"00:00:00.000+00:00"}, {"00:00:00.000+00:00"}),
        (
            "interval day to second",
            SENTINELS | {"-2", "0.5", "2:03", "1 02", "0 23:00:00.000000"},
            {"-2", "0.5", "2:03", "1 02", "0 23:00:00.000000"},
        ),
        ("interval year to month", SENTINELS | {"3", "-1-2"}, {"3", "-1-2"}),
        ("boolean", SENTINELS | {"false", "False", "0"}, {"false"}),
        ("uuid", SENTINELS | {_NIL, _NIL.upper()}, {_NIL}),
    ],
)
def test_a_type_holds_the_sentinels_of_the_texts_the_database_casts_its_values_to(
    kind: str, texts: Collection[str], held: Collection[str]
) -> None:
    assert dialect("trino://h/c/s").held(kind, texts) == held


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("bigint", "CAST(-12 AS bigint)"),
        ("decimal(12,0)", "CAST(-12 AS decimal(12,0))"),
        ("decimal(12,2)", "CAST(-0.5 AS decimal(12,2))"),
        ("double", "CAST(-1.5 AS double)"),
        ("double", "nan()"),
        ("real", "CAST(0 AS real)"),
        ("date", "DATE '0001-01-01'"),
        ("timestamp(3) with time zone", "CAST(TIMESTAMP '9999-12-31 23:59:59.999 UTC' AS date)"),
        ("time(3)", "TIME '12:34:56.789'"),
        ("time(3) with time zone", "TIME '12:34:56.789 +01:00'"),
        ("interval day to second", "INTERVAL '-2' DAY"),
        ("interval day to second", "CAST(INTERVAL '-2' DAY AS interval day to second)"),
        ("interval day to second", "INTERVAL '02:03' HOUR TO MINUTE"),
        ("interval year to month", "INTERVAL '-1-2' YEAR TO MONTH"),
        ("boolean", "false"),
        ("uuid", f"UUID '{_NIL}'"),
    ],
)
def test_a_type_holds_the_texts_the_database_casts_its_values_to(
    source: Source, kind: str, value: str
) -> None:
    # The statement is the test's own: a value of each type is had of no table of the simulation;
    # a moment is compared as its day, which `value` is of it.
    statement = f"SELECT trim(CAST({value} AS varchar))"
    ((text,),) = source.query(statement, f"writing {kind}")
    assert isinstance(text, str)
    assert source.dialect.held(kind, {text}) == {text}


@pytest.mark.parametrize(
    ("kind", "value", "text"),
    [
        ("double", "CAST(-1 AS double)", "-1.0E0"),
        ("boolean", "true", "true"),
        ("char(4)", "CAST('ab' AS char(4))", "ab"),
        ("time(9)", "TIME '12:34:56.123456789'", "12:34:56.123456789"),
        (
            "timestamp(9)",
            "TIMESTAMP '2024-01-31 12:34:56.123456789'",
            "2024-01-31 12:34:56.123456789",
        ),
        (
            "timestamp(3) with time zone",
            "TIMESTAMP '2024-01-31 12:00:00.000 Europe/Berlin'",
            "2024-01-31 12:00:00.000 Europe/Berlin",
        ),
        ("json", "JSON '\"N/A\"'", "N/A"),
        ("json", "JSON '[1,2]'", "[1,2]"),
    ],
)
def test_a_value_is_read_as_the_text_the_database_writes_it_as_of_all_its_digits(
    source: Source, kind: str, value: str, text: str
) -> None:
    # The statement is the test's own: a value of each type is had of no table of the simulation.
    statement = f"SELECT {source.dialect.text(value, kind)}"
    assert source.query(statement, f"reading {kind}") == [(text,)]


def test_a_value_of_a_type_the_database_writes_no_text_of_is_read_as_it_is(source: Source) -> None:
    statement = f"SELECT {source.dialect.text('ARRAY[1, 2]', 'array(integer)')}"
    assert source.query(statement, "reading an array") == [([1, 2],)]


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        *(("varchar(40)", text) for text in ("", " ", "NULL", "null", " N/A ", "n/a", "-")),
        *(("varchar(40)", text) for text in ("0001-01-01", "1900-01-01", "31.12.9999")),
        ("date", "9999-12-31"),
        ("timestamp(3)", "9999-12-31 23:59:59.999"),
        ("timestamp(3) with time zone", "9999-12-31 00:00:00.000 UTC"),
        ("json", "-"),
    ],
)
def test_a_value_read_is_a_sentinel_as_the_database_compares_it(kind: str, value: str) -> None:
    assert not dialect("trino://h/c/s").is_filled(kind, value, SENTINELS)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("varchar(40)", "10115"),
        *(("varchar(40)", text) for text in ("0", "00000", "Null", "--", "9999-12-31 00:00:00")),
        ("bigint", "0"),
        ("date", "2024-01-31"),
        ("timestamp(3)", "2024-01-31 00:00:00.000"),
        ("array(integer)", [1, 2]),
    ],
)
def test_a_value_read_that_is_no_sentinel_is_filled(kind: str, value: object) -> None:
    assert dialect("trino://h/c/s").is_filled(kind, value, SENTINELS)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("varchar(10)", "' N/A '"),
        ("varchar(20)", "'9999-12-31 00:00'"),
        ("char(4)", "CAST('-' AS char(4))"),
        ("double", "CAST(-1 AS double)"),
        ("timestamp(3)", "TIMESTAMP '9999-12-31 12:00:00.000'"),
        ("timestamp(3) with time zone", "TIMESTAMP '9999-12-31 23:00:00.000 -05:00'"),
        ("json", "JSON 'null'"),
        ("json", "JSON '\"N/A\"'"),
        ("json", "JSON '{\"a\": 1}'"),
    ],
)
def test_a_value_read_is_a_sentinel_where_the_database_counts_it_as_one(
    source: Source, kind: str, value: str
) -> None:
    trino = source.dialect
    texts = trino.held(kind, SENTINELS | {"-1.0E0"})
    # The statement is the test's own: a value of each type is had of no table of the simulation.
    read, counting = trino.text('"v"', kind), trino.sentinels("v", kind, texts)
    statement = f'SELECT max({read}), {counting} FROM (SELECT {value} AS "v")'
    ((text, counted),) = source.query(statement, f"comparing {kind}")
    assert trino.is_filled(kind, text, texts) == (counted == 0), text


@pytest.mark.parametrize(
    ("value", "pattern"),
    [("JSON '\"abc\"'", "abc"), ("JSON '{\"a\": 1}'", "[{].*[}]"), ("JSON 'null'", "null")],
)
def test_a_pattern_matches_a_value_as_it_is_read(source: Source, value: str, pattern: str) -> None:
    # The statement is the test's own: a value of JSON is had of no table of the simulation.
    matching = source.dialect.matching('"v"', "json", pattern)
    statement = f'SELECT {matching} FROM (SELECT {value} AS "v")'
    assert source.query(statement, "matching JSON") == [(1,)]


@pytest.mark.parametrize(
    ("kind", "text", "extent"),
    [
        ("timestamp(3)", "9999-12-31", ("9999-12-31 00:00:00.000", "9999-12-31 23:59:59.999")),
        ("timestamp(0)", "0001-01-01", ("0001-01-01 00:00:00", "0001-01-01 23:59:59")),
        (
            "timestamp(6) with time zone",
            "1900-01-01",
            ("1900-01-01 00:00:00.000000 +14:00", "1900-01-01 23:59:59.999999 -14:00"),
        ),
        ("date", "9999-12-31", ("9999-12-31", "9999-12-31")),
        ("varchar(10)", "N/A", ("N/A", "N/A")),
    ],
)
def test_a_sentinel_of_a_moment_stands_for_its_day_and_any_other_for_itself(
    kind: str, text: str, extent: tuple[str, str]
) -> None:
    assert dialect("trino://h/c/s").extent(kind, text) == extent


def test_the_extent_of_a_day_is_refused_of_a_type_of_moments_of_no_precision() -> None:
    with pytest.raises(ValueError, match="of moments of no precision"):
        dialect("trino://h/c/s").extent("timestamp", "9999-12-31")


@pytest.mark.parametrize("kind", ["timestamp(3)", "timestamp(0)", "timestamp(6) with time zone"])
def test_the_extent_of_a_day_is_of_moments_of_that_day_of_the_precision_of_the_type(
    source: Source, kind: str
) -> None:
    first, last = source.dialect.extent(kind, "9999-12-31")
    # The statement is the test's own: a value of each type is had of no table of the simulation.
    read = [f"CAST(CAST('{text}' AS {kind}) AS varchar)" for text in (first, last)]
    days = [f"CAST(CAST('{text}' AS {kind}) AS date)" for text in (first, last)]
    statement = f"SELECT {', '.join([*read, *days])}"
    found = source.query(statement, f"reading the extent of {kind}")
    assert found == [(first, last, date(9999, 12, 31), date(9999, 12, 31))], (
        "written as the database writes them, of the day in its own zone"
    )


@pytest.mark.parametrize(
    ("kind", "smaller", "larger"),
    [
        ("double", "-1.0E0", "5.0E-1"),
        ("decimal(12,2)", "9.50", "10.00"),
        ("time(3) with time zone", "23:00:00.000-05:00", "05:00:00.000+00:00"),
        ("time(3) with time zone", "00:00:00.000+00:00", "00:30:00.000+01:00"),
        ("time(3)", "09:00:00.000", "10:00:00.000"),
        ("date", "1900-01-01", "2024-01-31"),
        ("timestamp(3)", "2024-01-01 23:00:00.000", "2024-01-02 00:00:00.000"),
        (
            "timestamp(3) with time zone",
            "2024-01-02 00:00:00.000 +14:00",
            "2024-01-01 23:00:00.000 -14:00",
        ),
        (
            "timestamp(3) with time zone",
            "2024-01-01 09:00:00.000 +05:00",
            "2024-01-01 08:00:00.000 UTC",
        ),
        (
            "timestamp(3) with time zone",
            "2024-07-01 09:00:00.000 Europe/Berlin",
            "2024-07-01 08:00:00.000 UTC",
        ),
    ],
)
def test_values_are_in_the_order_of_the_database(
    source: Source, kind: str, smaller: str, larger: str
) -> None:
    trino = source.dialect
    assert sorted([larger, smaller], key=lambda text: trino.order(kind, text)) == [smaller, larger]
    # The statement is the test's own: a value of each type is had of no table of the simulation.
    statement = f"SELECT CAST('{smaller}' AS {kind}) < CAST('{larger}' AS {kind})"
    assert source.query(statement, f"ordering {kind}") == [(True,)]


def test_a_null_is_not_filled_and_of_a_column_of_no_sentinels_any_other_value_is() -> None:
    trino = dialect("trino://h/c/s")
    assert not trino.is_filled("varchar(40)", None, frozenset())
    assert trino.is_filled("varchar(40)", "", frozenset())


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
