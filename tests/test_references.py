"""Tests of the references between tables: of tables made by hand, and against the simulation.

The tests of tables made by hand answer the statements by a schema that finds, of every column
probed, the same share of its values in every key, and of every reference counted the same
coverage, and keeps the statements it was sent; those against the simulation environment need it
to run.
"""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from data_profiler.detect import EMAIL, PHONE, UUID
from data_profiler.overrides import Overrides, ReferenceOverride
from data_profiler.profile import (
    Cardinality,
    Column,
    Findings,
    Lengths,
    Match,
    Profile,
    Range,
    Reference,
    Statistics,
    Table,
    Value,
)
from data_profiler.references import find
from data_profiler.scan import scan
from data_profiler.source import Source, connect
from data_profiler.workspace import Workspace


class _Answering(Source):
    """A schema that finds `found` of the values probed in every key, and covers by `coverage`.

    The keys of the tables `by_table` find their share of the values probed instead.
    """

    def __init__(
        self,
        found: float = 1.0,
        coverage: float = 1.0,
        by_table: dict[str, float] | None = None,
        columns: dict[str, dict[str, str]] | None = None,
    ) -> None:
        with connect("trino://h/c/s", "u", "") as trino:
            super().__init__("crm", "sales", trino.dialect)
        self._found = found
        self._coverage = coverage
        self._by_table = by_table or {}
        self._columns = columns or {}
        self.sent: list[str] = []

    def columns(self, table: str) -> dict[str, str]:
        return self._columns[table]

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        self.sent.append(statement)
        if step == "probing the references":
            probes = statement.count(' AS "probe"')
            keys = re.findall(
                r'AS "key", CAST\("[^"]+" AS varchar\) AS "id" FROM "([^"]+)"', statement
            )
            return [
                (probe, key, 100, round(100 * self._by_table.get(table, self._found)))
                for probe in range(probes)
                for key, table in enumerate(keys)
            ]
        references = statement.count("LEFT JOIN")
        return [tuple(n for _ in range(references) for n in (1000, round(1000 * self._coverage)))]

    def close(self) -> None:
        pass


def _ranged(name: str, kind: str, distinct: int, smallest: int, largest: int) -> Column:
    """A column of no nulls of `kind`, of `distinct` values from `smallest` to `largest`."""
    statistics = Statistics(0, distinct, range=Range(str(smallest), str(largest)))
    return Column(name=name, type=kind, statistics=statistics)


def _guid(name: str, distinct: int) -> Column:
    """A column of no nulls of `distinct` UUIDs as text."""
    statistics = Statistics(0, distinct, Lengths(36, 36))
    return Column(name, "varchar(36)", statistics, matches=(Match(UUID, 1.0, 1.0),))


# A key of text of a semantic type, of numbers of a customer.
_NUMBER = Column(
    "cust_no", "varchar(12)", Statistics(0, 5000, Lengths(12, 12)), matches=(Match(PHONE, 1.0),)
)


def _keyed(name: str, rows: int, *columns: Column) -> Table:
    """A table `name` of `rows` rows, each of its `columns` a key."""
    return Table(name, rows, columns, keys=tuple((column.name,) for column in columns))


_CUST = _keyed(
    "cust",
    5000,
    _ranged("cust_id", "bigint", 5000, 100001, 105000),
    _guid("cust_guid", 5000),
    _NUMBER,
)


def _ordering(*columns: Column, keyed: tuple[Table, ...] = (_CUST,)) -> Profile:
    """A profile of the tables `keyed` and of a table `ord` of 20,000 rows of `columns`."""
    ordered = Table(name="ord", rows=20000, columns=columns)
    return Profile(catalog="crm", schema="sales", tables=(*keyed, ordered))


def _ordered(found: Profile) -> Table:
    return found.table("ord")


def test_a_column_found_in_one_key_alone_refers_to_it_with_its_coverage() -> None:
    profile = _ordering(_ranged("cust_id", "bigint", 4000, 100001, 104999))
    source = _Answering(coverage=0.98)
    assert _ordered(find(source, profile, {})).references == (
        Reference("cust_id", "cust", "cust_id", 0.98),
    )
    assert len(source.sent) == 2, "probed, then counted"


def _lists(name: str, items: Statistics) -> Column:
    """A column of lists `name`, of no nulls, whose values have `items`."""
    statistics = Statistics(0, 3000, Lengths(1, 41))
    return Column(name, "varchar(41)", statistics, list_separator=";", items=Findings(items))


# The columns of `ord` of lists of customers, for its source of the values of their lists.
_LISTED = {"ord": {"cust_ids": "varchar(41)", "cust_id": "bigint"}}


def test_the_values_of_lists_of_numbers_refer_to_a_key_of_numbers_by_queries_of_their_own() -> None:
    listed = _lists("cust_ids", Statistics(0, 400, Lengths(6, 6), Range("100001", "104999")))
    profile = _ordering(listed, _ranged("cust_id", "bigint", 4000, 100001, 104999))
    source = _Answering(columns=_LISTED)
    ordered = _ordered(find(source, profile, {}))
    reference = Reference("cust_ids", "cust", "cust_id", 1.0)
    assert reference in ordered.references, "of the values of its lists, as numbers"
    assert ordered.cardinality(reference) is Cardinality.MANY_TO_MANY
    unnested = [statement for statement in source.sent if "UNNEST" in statement]
    assert len(unnested) == 2, "probed, then counted, apart from the other column"
    assert len(source.sent) == 4, "and the other column probed and counted on the table"


def test_the_values_of_lists_of_digits_of_several_lengths_refer_whatever_their_range_of_texts() -> (
    None
):
    # A key numbered from one, whose values of lists of 1 to 4 digits end as texts at 999.
    keyed = (_keyed("cust", 5000, _ranged("cust_id", "bigint", 5000, 1, 5000)),)
    listed = _lists("cust_ids", Statistics(0, 4000, Lengths(1, 4), Range("1", "999")))
    profile = _ordering(listed, keyed=keyed)
    found = _ordered(find(_Answering(columns=_LISTED), profile, {}))
    assert found.references == (Reference("cust_ids", "cust", "cust_id", 1.0),), (
        "no run, as its range of texts is no range of its numbers"
    )


@pytest.mark.parametrize(
    "items",
    [
        Statistics(0, 400, Lengths(6, 6), Range("A00001", "A04999")),
        Statistics(0, 400, Lengths(6, 6)),
    ],
    ids=["of letters", "of no range"],
)
def test_the_values_of_lists_of_no_numbers_do_not_refer_to_a_key_of_numbers(
    items: Statistics,
) -> None:
    profile = _ordering(_lists("cust_ids", items))
    source = _Answering(columns=_LISTED)
    assert _ordered(find(source, profile, {})).references == ()
    assert source.sent == [], "not indicated, as texts against numbers"


def test_the_values_of_lists_of_texts_refer_to_a_key_of_texts() -> None:
    listed = _lists("cust_nos", Statistics(0, 400, Lengths(12, 12)))
    columns = {"ord": {"cust_nos": "varchar(41)"}}
    found = _ordered(find(_Answering(columns=columns), _ordering(listed), {}))
    assert found.references == (Reference("cust_nos", "cust", "cust_no", 1.0),)


def test_a_column_of_lists_is_not_searched_for_a_reference_to_a_key_of_its_own_table() -> None:
    listed = _lists("ord_ids", Statistics(0, 400, Lengths(1, 3), Range("1", "999")))
    ordered = Table(
        name="ord",
        rows=20000,
        columns=(_ranged("ord_id", "bigint", 20000, 1, 20000), listed),
        keys=(("ord_id",),),
    )
    profile = Profile(catalog="crm", schema="sales", tables=(ordered,))
    source = _Answering(columns={"ord": {"ord_id": "bigint", "ord_ids": "varchar(41)"}})
    assert find(source, profile, {}).table("ord").references == ()
    assert source.sent == [], "its values would be read with the key"


def test_a_reference_given_of_a_column_of_lists_is_measured_by_the_values_of_its_lists() -> None:
    listed = _lists("cust_ids", Statistics(0, 400, Lengths(6, 6), Range("100001", "104999")))
    source = _Answering(coverage=0.95, columns=_LISTED)
    found = find(source, _ordering(listed), {"ord": {"cust_ids": _GIVEN}})
    assert _ordered(found).references == (
        Reference("cust_ids", "cust", "cust_id", 0.95, given=True),
    )
    (counted,) = source.sent
    assert "UNNEST" in counted, "counted on the values of its lists"


def test_unmistakable_values_refer_to_their_key_by_the_probe_alone() -> None:
    profile = _ordering(_guid("cust_guid", 3000))
    source = _Answering(found=0.51)
    assert _ordered(find(source, profile, {})).references == (
        Reference("cust_guid", "cust", "cust_guid", None),
    )
    assert len(source.sent) == 1, "no coverage counted"
    assert _ordered(find(_Answering(found=0.5), profile, {})).references == (), "not more than half"


@pytest.mark.parametrize(
    ("found", "coverage", "queries"),
    [(0.79, 1.0, 1), (0.8, 0.89, 2)],
    ids=["too few probed", "too little covered"],
)
def test_a_column_too_few_of_whose_values_are_found_refers_to_none(
    found: float, coverage: float, queries: int
) -> None:
    profile = _ordering(_ranged("cust_id", "bigint", 4000, 100001, 104999))
    source = _Answering(found, coverage)
    assert _ordered(find(source, profile, {})).references == ()
    assert len(source.sent) == queries


@pytest.mark.parametrize(
    "column",
    [
        _ranged("cust_id", "date", 4000, 100001, 104999),
        _ranged("cust_id", "bigint", 8000, 100001, 104999),
        Column("cust_no", "varchar(12)", Statistics(0, 4000, Lengths(10, 12))),
        Column(
            "cust_no", "varchar(12)", Statistics(0, 4000, Lengths(12, 12)), (Match(EMAIL, 1.0),)
        ),
        _ranged("cust_id", "bigint", 4000, 1, 4000),
        _ranged("qty", "bigint", 25, 100001, 100025),
        Column("cust_no", "varchar(36)", Statistics(0, 4000, Lengths(36, 36))),
    ],
    ids=["types", "distinct", "lengths", "matches", "range", "run", "unmistakable"],
)
def test_a_column_the_profile_does_not_indicate_as_a_reference_is_not_probed(
    column: Column,
) -> None:
    source = _Answering()
    assert _ordered(find(source, _ordering(column), {})).references == ()
    assert source.sent == []


def test_a_run_of_whole_numbers_whose_name_agrees_with_the_key_is_probed() -> None:
    source = _Answering()
    profile = _ordering(_ranged("cust_id", "bigint", 25, 100001, 100025))
    assert _ordered(find(source, profile, {})).references == (
        Reference("cust_id", "cust", "cust_id", 1.0),
    )


def test_a_column_of_nearly_every_value_of_its_key_refers_to_it_whatever_its_name() -> None:
    profile = _ordering(_ranged("owner", "bigint", 4990, 100001, 105000))
    assert _ordered(find(_Answering(), profile, {})).references == (
        Reference("owner", "cust", "cust_id", 1.0),
    ), "not a run short of the end of the key"


@pytest.mark.parametrize(("name", "probed"), [("ord_no", False), ("cust_id", True)])
def test_a_key_numbered_from_one_refers_to_another_only_where_its_name_agrees(
    name: str, probed: bool
) -> None:
    keyed = _keyed("ord", 5000, _ranged(name, "bigint", 5000, 100001, 105000))
    source = _Answering()
    find(source, Profile(catalog="crm", schema="sales", tables=(_CUST, keyed)), {})
    assert bool(source.sent) == probed, "any key numbered from one holds one of as many values"


def test_a_profile_of_no_keys_is_not_queried() -> None:
    source = _Answering()
    unkeyed = Table("cust", 5000, _CUST.columns)
    found = find(
        source, _ordering(_ranged("cust_id", "bigint", 4000, 1, 4000), keyed=(unkeyed,)), {}
    )
    assert (_ordered(found).references, source.sent) == ((), [])


def test_a_column_found_in_several_keys_has_each_as_a_candidate_ranked() -> None:
    prtnr = _keyed("prtnr", 6000, _ranged("prtnr_id", "bigint", 6000, 100001, 106000))
    profile = _ordering(_ranged("ref_id", "bigint", 3000, 100001, 104990), keyed=(prtnr, _CUST))
    ordered = _ordered(find(_Answering(), profile, {}))
    assert ordered.references == ()
    assert ordered.reference_candidates == (
        Reference("ref_id", "cust", "cust_id", 1.0),
        Reference("ref_id", "prtnr", "prtnr_id", 1.0),
    ), "the span of the values of the customers fits theirs, not that of the partners"


def test_unmistakable_values_of_several_keys_refer_to_the_one_of_the_fewest_rows() -> None:
    prtnr = _keyed("prtnr", 6000, _guid("prtnr_guid", 6000))
    profile = _ordering(_guid("ref_guid", 3000), keyed=(prtnr, _CUST))
    assert _ordered(find(_Answering(), profile, {})).references == (
        Reference("ref_guid", "cust", "cust_guid", None),
    ), "as found in both"


def test_a_column_whose_range_reaches_beyond_its_key_is_probed() -> None:
    source = _Answering()
    profile = _ordering(_ranged("cust_id", "bigint", 4000, 100001, 105400))
    assert len(_ordered(find(source, profile, {})).references) == 1, (
        "of rows whose reference is lost"
    )


def test_the_range_of_texts_is_compared_as_texts_whatever_they_read_as() -> None:
    def digits(name: str, smallest: str, largest: str) -> Column:
        statistics = Statistics(0, 100, Lengths(1, 4), Range(smallest, largest))
        return Column(name, "varchar(4)", statistics)

    code = _keyed("code", 2000, digits("code_no", "1", "999"))
    for column in (digits("code_no", "1000", "1099"), digits("code_no", "1000", "NaN")):
        source = _Answering()
        assert _ordered(find(source, _ordering(column, keyed=(code,)), {})).references == (
            Reference("code_no", "code", "code_no", 1.0),
        ), "'1000' lies within '1' and '999' as text"


@pytest.mark.parametrize(
    ("table", "column"),
    [
        (_keyed("cust", 5000, _ranged("cust_id", "bigint", 5000, 1, 5000)), "cust_seg_no"),
        (_keyed("prtnr", 6000, _ranged("id", "bigint", 6000, 1, 6000)), "id"),
    ],
    ids=["the prefix of its table", "the name of a key of another"],
)
def test_a_run_whose_name_shares_less_than_the_terms_of_the_key_and_its_table_is_not_probed(
    table: Table, column: str
) -> None:
    source = _Answering()
    found = find(source, _ordering(_ranged(column, "bigint", 5, 1, 5), keyed=(table,)), {})
    assert (_ordered(found).references, source.sent) == ((), [])


def test_the_references_of_more_keys_than_ten_are_probed_and_counted_in_several_queries() -> None:
    keyed = tuple(
        _keyed(f"k{place:02}", 5000, _ranged("id", "bigint", 5000, 100001, 105000))
        for place in range(11)
    )
    source = _Answering()
    found = find(source, _ordering(_ranged("ref", "bigint", 3000, 100001, 104990), keyed=keyed), {})
    assert len(_ordered(found).reference_candidates) == 11
    probed, counted = source.sent[:2], source.sent[2:]
    assert [statement.count(' AS "key"') for statement in probed] == [10, 1]
    assert [statement.count("LEFT JOIN") for statement in counted] == [10, 1]


def test_the_sentinels_of_a_column_are_left_aside_as_nulls_where_it_is_probed() -> None:
    statistics = Statistics(0, 4000, range=Range("100001", "104999"), sentinels=(Value("0", 9),))
    source = _Answering()
    find(source, _ordering(Column("cust_id", "bigint", statistics)), {})
    assert "CASE WHEN trim(try_cast(\"cust_id\" AS varchar)) IN ('0') THEN NULL" in source.sent[0]


def test_the_references_and_candidates_a_profile_had_are_replaced() -> None:
    profile = _ordering(_ranged("cust_id", "date", 4000, 100001, 104999))
    ordered = replace(
        profile.table("ord"),
        references=(Reference("cust_id", "cust", "cust_id", 1.0),),
        reference_candidates=(Reference("cust_id", "cust", "cust_guid", 1.0),) * 2,
    )
    stale = replace(profile, tables=(_CUST, ordered))
    assert _ordered(find(_Answering(), stale, {})) == replace(
        ordered, references=(), reference_candidates=()
    )


def test_candidates_of_no_span_known_are_ranked_by_their_names_then_their_rows() -> None:
    def number(table: str, rows: int) -> Table:
        return _keyed(
            table, rows, Column(f"{table}_no", "varchar(12)", Statistics(0, rows, Lengths(12, 12)))
        )

    keyed = (number("prtnr", 6000), number("lead", 4000), number("cust", 5000))
    column = Column("cust_no", "varchar(12)", Statistics(0, 3000, Lengths(12, 12)))
    candidates = _ordered(
        find(_Answering(), _ordering(column, keyed=keyed), {})
    ).reference_candidates
    assert [reference.table for reference in candidates] == ["cust", "lead", "prtnr"]


def test_unmistakable_values_of_several_keys_refer_to_the_one_of_the_most_found() -> None:
    prtnr = _keyed("prtnr", 6000, _guid("prtnr_guid", 6000))
    profile = _ordering(_guid("ref_guid", 3000), keyed=(prtnr, _CUST))
    source = _Answering(by_table={"prtnr": 0.9, "cust": 0.6})
    assert _ordered(find(source, profile, {})).references == (
        Reference("ref_guid", "prtnr", "prtnr_guid", None),
    )


_GIVEN = ReferenceOverride("cust", "cust_id")


def test_a_reference_given_is_measured_rather_than_searched() -> None:
    source = _Answering(coverage=0.95)
    profile = _ordering(_ranged("cust_id", "bigint", 4000, 100001, 104999))
    found = find(source, profile, {"ord": {"cust_id": _GIVEN}})
    assert _ordered(found).references == (
        Reference("cust_id", "cust", "cust_id", 0.95, given=True),
    )
    assert len(source.sent) == 1, "its coverage counted, not probed"


@pytest.mark.parametrize(
    ("column", "given", "answering", "warned"),
    [
        (
            _ranged("cust_id", "bigint", 4000, 100001, 104999),
            _GIVEN,
            _Answering(coverage=0.5),
            "which holds 50% of its values",
        ),
        (
            _guid("cust_guid", 3000),
            ReferenceOverride("cust", "cust_guid"),
            _Answering(found=0.4),
            "most of whose values probed are not found in it",
        ),
        (
            _ranged("cust_id", "bigint", 4000, 100001, 104999),
            ReferenceOverride("cust", "cust_note"),
            _Answering(),
            "which is no key of one column",
        ),
        (
            replace(_guid("cust_guid", 0), statistics=Statistics(20000, 0)),
            ReferenceOverride("cust", "cust_guid"),
            _Answering(found=0.0),
            "most of whose values probed are not found in it",
        ),
    ],
    ids=["covered too little", "probed too few", "no key", "no values"],
)
def test_a_reference_given_that_would_not_be_found_is_warned_of_and_kept(
    caplog: pytest.LogCaptureFixture,
    column: Column,
    given: ReferenceOverride,
    answering: _Answering,
    warned: str,
) -> None:
    noted = replace(
        _CUST, columns=(*_CUST.columns, Column("cust_note", "bigint", Statistics(0, 9)))
    )
    found = find(answering, _ordering(column, keyed=(noted,)), {"ord": {column.name: given}})
    (reference,) = _ordered(found).references
    assert (reference.table, reference.key, reference.given) == (given.table, given.column, True)
    assert caplog.messages == [
        f"The overrides give ord.{column.name} as a reference to {given.table}.{given.column},"
        f" {warned}"
    ]


def test_a_column_given_no_reference_has_none_and_no_candidates_and_is_not_probed() -> None:
    source = _Answering()
    profile = _ordering(_ranged("cust_id", "bigint", 4000, 100001, 104999))
    ordered = _ordered(find(source, profile, {"ord": {"cust_id": False}}))
    assert (ordered.references, ordered.reference_candidates, source.sent) == ((), (), [])


def test_the_references_of_the_simulation_are_found(
    source: Source, example: Profile, tmp_path: Path
) -> None:
    workspace = Workspace.open(tmp_path / "workspace", example.catalog, example.schema)
    scan(source, re.compile(".*"), workspace, (), ";", Overrides(), tmp_path / "profile")
    found = find(source, Profile.read(tmp_path / "profile"), {})
    for table in example.tables:
        related = found.table(table.name)
        for made in table.references:
            if made in related.references:
                continue
            ranked = [c for c in related.reference_candidates if c.column == made.column]
            assert ranked[0] == made, f"{table.name}.{made.column}: the first of its candidates"
    for table in found.tables:
        given = example.table(table.name).references
        assert set(table.references) <= set(given), (
            f"{table.name}: no reference it was not made with"
        )
    columns = {(table.name, r.column) for table in found.tables for r in table.references}
    candidates = {
        (table.name, r.column) for table in found.tables for r in table.reference_candidates
    }
    for code in (("ord_itm", "qty"), ("ord_itm", "pos_no"), ("prtnr", "lead_scr")):
        assert code not in columns | candidates, f"{code}: a code refers to no key"
    for key in (("cust", "cust_id"), ("cntct", "cntct_id"), ("prtnr", "prtnr_id")):
        assert key not in columns | candidates, f"{key}: a key numbered from one, as others are"
    assert ("ord", "cntct_uuid") in columns, "unmistakable values, of their type"
    assert ("ord", "dlvr_addr_guid") in columns, "unmistakable values, as text"
