"""The database the tool reads: a schema of it, its tables and columns, and the queries sent to it.

A `Source` sends queries and nothing else, lists the tables and columns of its schema, and reads a
table grouped by each of some columns alone, in one pass. Every statement it sends is written by its
`Dialect`: whole, where it lists them, and of the building blocks the dialect offers, where another
part counts or samples what the tables hold. A failure is told by the database, its endpoint and
what was done; what the database said, which may hold a value of it, stays in the cause of the
error. Trino is reached by HTTPS, whose certificates and proxies come from the variables of the
process, as `requests` reads them: `REQUESTS_CA_BUNDLE` for a certificate of a CA of one's own,
`NO_PROXY` for a database a proxy does not reach.
"""

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from re import Pattern
from types import TracebackType
from typing import Final, Self
from urllib.parse import urlsplit

from trino import dbapi
from trino.auth import BasicAuthentication
from trino.dbapi import Connection
from trino.exceptions import Error as TrinoError
from trino.exceptions import HttpError

_logger = logging.getLogger(__name__)

# The port of Trino where a URL names none: that of HTTPS.
_PORT: Final = 443

# The form of a URL of Trino, for the messages of a URL that has another.
_FORM: Final = "trino://host:port/catalog/schema"

# The types of Trino whose values are texts, and those of whole numbers, by how their names begin.
_TEXTS: Final = ("varchar", "char")
_WHOLE: Final = ("tinyint", "smallint", "integer", "bigint")

# The types of Trino whose values have an order, by how their names begin - `time` also those of
# `timestamp` -: those of others, such as `json` or `map`, would make `min` and `max` fail the
# query they are in; a range of binaries would say nothing.
_ORDERED: Final = (
    *_TEXTS,
    *_WHOLE,
    "real",
    "double",
    "decimal",
    "date",
    "time",
    "interval",
    "boolean",
    "uuid",
)

# The types of Trino whose values it casts to a text, by how their names begin: those of others,
# such as an array, a map, a row or a binary, would make the cast fail the query it is in.
_HAVE_TEXT: Final = (*_ORDERED, "json")

# The types of Trino of the keys a database generates, by how their names begin: whole numbers and
# UUIDs - and decimals of no fraction, as which Trino reads the keys of some databases.
_SURROGATE: Final = (*_WHOLE, "uuid")
_WHOLE_DECIMAL: Final = re.compile(r"decimal\(\d+,\s*0\)")
# A decimal of a scale, whose values with as many digits after the point are the same as text.
_DECIMAL: Final = re.compile(r"decimal\(\d+,\s*(\d+)\)")

# The types of Trino whose values identify a row, by how their names begin: exact values, not those
# of floating point or of time, which are unique by chance, nor booleans, binaries or structures.
_IDENTIFYING: Final = (*_TEXTS, *_SURROGATE, "decimal", "date")

# The types of Trino whose values are moments, by how their names begin, compared as their days.
_MOMENTS: Final = ("timestamp",)

# The standard error of the distinct values Trino counts: half a percent, against its default of
# 2.3, so that keys and enumerations can be told by them, for about 64 KB of memory per column.
_DISTINCT_ERROR: Final = 0.005


class SourceError(Exception):
    """A failure of the database: the database by its endpoint, and what was done."""


@dataclass(frozen=True)
class Probe:
    """The values of a column to probe in keys, taken of a share of the rows of its table.

    Attributes:
        table: The table of the column, of the schema of the source.
        values: The expression of the values of the column, as `Dialect.without` writes it.
        percent: The share of the rows of the table taken, each with this chance.
    """

    table: str
    values: str
    percent: float


@dataclass(frozen=True)
class Lookup:
    """The values of a column of a table to look up in a key of one column.

    Attributes:
        values: The expression of the values of the column, as `Dialect.without` writes it.
        table: The table of the key, of the schema of the source.
        key: The column of the key, of a value in each row at most.
    """

    values: str
    table: str
    key: str


class Dialect(ABC):
    """The SQL of one kind of database: the statements and expressions the tool sends.

    Its building blocks take the names of tables and columns as they are, and quote them; those that
    count or measure values take an expression of the values of a column, as `column` or `without`
    writes it. Those of the sentinels take a column and its type, as they compare the values of the
    column itself, a moment as its day.
    """

    @abstractmethod
    def tables(self, catalog: str, schema: str) -> str:
        """The statement listing the names of the tables of `schema` in `catalog`."""

    @abstractmethod
    def columns(self, catalog: str, schema: str, table: str) -> str:
        """The statement listing the names and types of the columns of `table`, in order."""

    @abstractmethod
    def select(self, expressions: Sequence[str], table: str) -> str:
        """The statement selecting `expressions` from `table` of the schema of the source."""

    @abstractmethod
    def sampled(self, expressions: Sequence[str], table: str, percent: float, limit: int) -> str:
        """The statement selecting `expressions` of a share of the rows of `table`, at random.

        Args:
            expressions: The expressions to select.
            table: The table, of the schema of the source.
            percent: The share of the rows, each taken with this chance.
            limit: The most rows the statement returns.
        """

    @abstractmethod
    def grouped(self, expressions: Sequence[str], table: str, columns: Sequence[str]) -> str:
        """The statement selecting `expressions` from `table`, grouped by each of `columns` alone.

        The table is read once for all the columns. A row of the statement belongs to the groups
        of one of them, which `grouping` tells; the others are null in it.

        Args:
            expressions: The expressions to select.
            table: The table, of the schema of the source.
            columns: The columns to group by, each on its own.
        """

    @abstractmethod
    def probed(self, probes: Sequence[Probe], keys: Sequence[tuple[str, str]], limit: int) -> str:
        """The statement counting, of `limit` values taken of each probe, those found in each key.

        The values of a probe are taken of a share of the rows of its table, its nulls left out,
        and looked up in the whole column of each key, both compared as text; the keys are read
        once, and the values taken are held in memory, not those of the keys. A row of the
        statement is of a probe, by its place, and of a key, by its place, where any of the values
        taken are found in the key: how many values were taken of the probe, and how many of them
        are found.

        Args:
            probes: The values to probe.
            keys: Of each key, its table and its column, of a value in each row at most.
            limit: The most values taken of a probe.
        """

    @abstractmethod
    def covered(self, table: str, lookups: Sequence[Lookup]) -> str:
        """The statement counting, of each of `lookups` of `table`, its values found in its key.

        The table is read once for all of them, and each value looked up in the whole column of its
        key, both compared as text. The one row of the statement holds, of each lookup in their
        order, two counts: of its values, and of those found in its key.

        Args:
            table: The table of the values looked up, of the schema of the source.
            lookups: The values to look up, each in its key.
        """

    @abstractmethod
    def column(self, column: str) -> str:
        """The expression of the values of `column`."""

    @abstractmethod
    def sentinels(self, column: str, kind: str, texts: Collection[str]) -> str:
        """The expression counting the values of `column`, of the type `kind`, one of `texts`.

        A value is compared as text, its spaces at either end cut, and a moment as the text of its
        day, as `detect` compares the values of a sample; `kind` is a type that `has_text`, and
        `texts` are one at least. Texts, days and moments are written alike by the database and by
        Python; truth values and floating numbers are not, `true` and `True`, `0.0E0` and `0.0`.
        """

    @abstractmethod
    def without(self, column: str, kind: str, texts: Collection[str]) -> str:
        """The expression of the values of `column`, null where a value is one of `texts`.

        A value is compared as `sentinels` compares it; where `texts` are none, the expression is
        that of `column`, of any type.
        """

    @abstractmethod
    def grouping(self, column: str) -> str:
        """The expression that is 0 in the rows grouped by `column`, and 1 in the others."""

    @abstractmethod
    def rows(self) -> str:
        """The expression counting the rows."""

    @abstractmethod
    def nulls(self, values: str) -> str:
        """The expression counting the nulls of `values`."""

    @abstractmethod
    def distinct(self, values: str) -> str:
        """The expression counting the distinct values of `values`, approximately."""

    @abstractmethod
    def exactly_distinct(self, columns: Sequence[str]) -> str:
        """The expression counting the distinct values of `columns` together, exactly.

        Each count holds the distinct values of the rows it is counted of in memory, as many as
        the rows where they are unique: dearer than `distinct`, of few columns at once.
        """

    @abstractmethod
    def distinct_error(self) -> float:
        """The standard error of the distinct values `distinct` counts, as a share of them."""

    @abstractmethod
    def smallest(self, values: str) -> str:
        """The expression of the smallest of `values`."""

    @abstractmethod
    def largest(self, values: str) -> str:
        """The expression of the largest of `values`."""

    @abstractmethod
    def shortest(self, values: str) -> str:
        """The expression of the length of the shortest of `values`."""

    @abstractmethod
    def longest(self, values: str) -> str:
        """The expression of the length of the longest of `values`."""

    @abstractmethod
    def matching(self, values: str, pattern: str) -> str:
        """The expression counting those of `values` that `pattern` matches whole.

        Each value is matched as text, its spaces at either end cut; `values` are of a type the
        database casts to a text, not an array, a map, a row or a binary, which fail the query.
        `pattern` is a regular expression of what Python and the database share.
        """

    @abstractmethod
    def is_text(self, kind: str) -> bool:
        """Whether a column of the type `kind`, as the database names it, holds texts."""

    @abstractmethod
    def is_ordered(self, kind: str) -> bool:
        """Whether the values of a column of the type `kind` have an order, and so a range."""

    @abstractmethod
    def has_text(self, kind: str) -> bool:
        """Whether the database writes the values of a column of the type `kind` as text."""

    @abstractmethod
    def identifies(self, kind: str) -> bool:
        """Whether the values of a column of the type `kind` may identify its rows, being exact."""

    @abstractmethod
    def is_surrogate(self, kind: str) -> bool:
        """Whether the type `kind` is one of the keys a database generates: whole numbers, UUIDs."""

    @abstractmethod
    def is_unmistakable(self, kind: str) -> bool:
        """Whether values of the type `kind` equal those of another column by no chance: UUIDs."""

    @abstractmethod
    def is_same_family(self, kind: str, other: str) -> bool:
        """Whether values of the types `kind` and `other` are the same where their texts are."""


class Source(ABC):
    """A schema of a database the tool reads, by queries only; closed as a context manager.

    Attributes:
        catalog: The catalog of the schema.
        schema: The schema whose tables are read.
        dialect: The SQL of the database.
    """

    def __init__(self, catalog: str, schema: str, dialect: Dialect) -> None:
        """Takes the schema the source reads, and the dialect of its database."""
        self.catalog: Final = catalog
        self.schema: Final = schema
        self.dialect: Final = dialect

    @abstractmethod
    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        """Sends `statement` to the database, and returns its rows once it has run.

        The statement runs in the schema of the source: a table of it needs no catalog and no
        schema before its name.

        Args:
            statement: The statement, as the dialect wrote it.
            step: What the statement does, such as "listing the tables of crm.sales", for the
                message of a failure.

        Raises:
            SourceError: The database cannot be reached, refuses the user, or fails at `step`.
        """

    @abstractmethod
    def close(self) -> None:
        """Closes the connection to the database."""

    def name(self, table: str) -> str:
        """The name of `table` with the catalog and schema of the source, as messages name it."""
        return f"{self.catalog}.{self.schema}.{table}"

    def tables(self, pattern: Pattern[str]) -> list[str]:
        """The names of the tables of the schema that `pattern` matches whole, sorted.

        Raises:
            SourceError: The database fails to list them.
        """
        statement = self.dialect.tables(self.catalog, self.schema)
        names = self.query(statement, f"listing the tables of {self.catalog}.{self.schema}")
        return sorted(str(name) for (name,) in names if pattern.fullmatch(str(name)))

    def columns(self, table: str) -> dict[str, str]:
        """The columns of `table`, by name, with their types as the database names them, in order.

        Raises:
            SourceError: The schema has no such table, or the database fails to list its columns.
        """
        statement = self.dialect.columns(self.catalog, self.schema, table)
        found = self.query(statement, f"listing the columns of {self.name(table)}")
        if not found:
            raise SourceError(f"{self.catalog}.{self.schema} has no table {table}")
        return {str(column): str(kind) for column, kind in found}

    def grouped(
        self, table: str, columns: Sequence[str], expressions: Sequence[str], step: str
    ) -> list[tuple[int, object, tuple[object, ...]]]:
        """The groups of `table` by each of `columns` alone, each with `expressions` of its rows.

        The table is read once for all the columns, by one statement `Dialect.grouped` writes.

        Args:
            table: The table, of the schema of the source.
            columns: The columns to group by, each on its own.
            expressions: The expressions of the rows of each group, as the dialect writes them.
            step: What the statement does, for the message of a failure.

        Returns:
            Each group: the place of its column among `columns`, its value of the column - None
            of the rows the column is null in -, and the values of `expressions` of its rows.

        Raises:
            SourceError: The database fails at `step`.
            TypeError: A row is grouped by other than one column, which the dialect would have to
                make sure of.
        """
        dialect = self.dialect
        grouping = [*map(dialect.column, columns), *map(dialect.grouping, columns)]
        statement = dialect.grouped([*grouping, *expressions], table, columns)
        groups = []
        for row in self.query(statement, step):
            # The row belongs to the one column whose grouping is 0; the others are null in it.
            groupings = row[len(columns) : 2 * len(columns)]
            if groupings.count(0) != 1:
                raise TypeError(f"the query grouped a row of {table} by other than one column")
            index = groupings.index(0)
            groups.append((index, row[index], row[2 * len(columns) :]))
        return groups

    def __enter__(self) -> Self:
        """Returns the source, whose connection is closed at the end of the block."""
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Closes the connection to the database."""
        self.close()


def connect(url: str, user: str, password: str) -> Source:
    """Connects to the schema `url` names, as `user`.

    Args:
        url: The schema, as `trino://host:port/catalog/schema`; the port is 443 if none is given.
            Trino is reached by HTTPS.
        user: The user the schema is read as.
        password: The password of the user.

    Returns:
        The source; the database is reached first when a statement is sent to it.

    Raises:
        SourceError: The URL is not of Trino, holds a user, a password, a query or a fragment, or
            lacks the host, the catalog or the schema, or the user is empty. The message never
            repeats the URL, which may hold a password.
    """
    parts = urlsplit(url)
    if parts.scheme != "trino":
        raise SourceError(f"only a URL of Trino is read, {_FORM}, not of {parts.scheme or 'none'}")
    # A URL that holds a password holds a user too, if an empty one.
    if parts.username is not None:
        raise SourceError("the URL holds a user or a password, which are given apart from it")
    if parts.query or parts.fragment:
        raise SourceError(
            f"the URL has a query or a fragment, which a URL of Trino has not: {_FORM}"
        )
    try:
        port = parts.port or _PORT
    except ValueError as error:
        raise SourceError("the port of the URL is no number from 0 to 65535") from error
    path = parts.path.strip("/").split("/")
    if not parts.hostname or len(path) != 2 or not all(path):
        raise SourceError(f"the URL lacks host, catalog or schema: {_FORM}")
    if not user:
        raise SourceError("the user to read the schema as is empty")
    catalog, schema = path
    connection: Connection = dbapi.connect(  # type: ignore[no-untyped-call]  # no annotations
        host=parts.hostname,
        port=port,
        http_scheme="https",
        user=user,
        auth=BasicAuthentication(user, password),
        catalog=catalog,
        schema=schema,
    )
    return _TrinoSource(connection, catalog, schema)


class _TrinoSource(Source):
    """A schema of a Trino or Starburst, reached by HTTPS with a password."""

    def __init__(self, connection: Connection, catalog: str, schema: str) -> None:
        """Takes the connection to Trino, made for the schema that is read."""
        super().__init__(catalog, schema, _TrinoDialect())
        self._connection = connection
        self._endpoint = f"Trino at https://{connection.host}:{connection.port}"

    def query(self, statement: str, step: str) -> list[tuple[object, ...]]:
        """Sends `statement` to Trino, and returns its rows once it has run."""
        _logger.debug("Sending to %s, %s: %s", self._endpoint, step, statement)
        try:
            cursor = self._connection.cursor()
            cursor.execute(statement)
            rows: list[list[object]] = cursor.fetchall()
        except HttpError as error:
            # The client tells a refused login only by the status in the text of its error.
            if str(error).startswith("error 401"):
                user = self._connection.user
                raise SourceError(
                    f"{self._endpoint} refused the user {user}: user or password is wrong"
                ) from error
            raise SourceError(f"{self._endpoint} failed {step}") from error
        except TrinoError as error:
            raise SourceError(f"{self._endpoint} failed {step}") from error
        return [tuple(row) for row in rows]

    def close(self) -> None:
        """Closes the connection to Trino."""
        self._connection.close()  # type: ignore[no-untyped-call]  # no annotations


class _TrinoDialect(Dialect):
    """The SQL of Trino and Starburst."""

    def tables(self, catalog: str, schema: str) -> str:
        """The statement listing the names of the tables of `schema` in `catalog`."""
        return (
            f"SELECT table_name FROM {_identifier(catalog)}.information_schema.tables "
            f"WHERE table_schema = {_literal(schema)}"
        )

    def columns(self, catalog: str, schema: str, table: str) -> str:
        """The statement listing the names and types of the columns of `table`, in order."""
        return (
            f"SELECT column_name, data_type FROM {_identifier(catalog)}.information_schema.columns "
            f"WHERE table_schema = {_literal(schema)} AND table_name = {_literal(table)} "
            "ORDER BY ordinal_position"
        )

    def select(self, expressions: Sequence[str], table: str) -> str:
        """The statement selecting `expressions` from `table` of the schema of the source."""
        return f"SELECT {', '.join(expressions)} FROM {_identifier(table)}"

    def sampled(self, expressions: Sequence[str], table: str, percent: float, limit: int) -> str:
        """The statement selecting `expressions` of a share of the rows of `table`, at random."""
        return (
            f"SELECT {', '.join(expressions)} FROM {_identifier(table)} "
            f"TABLESAMPLE BERNOULLI ({percent:.10f}) LIMIT {limit}"
        )

    def grouped(self, expressions: Sequence[str], table: str, columns: Sequence[str]) -> str:
        """The statement selecting `expressions` from `table`, grouped by each of `columns`."""
        sets = ", ".join(f"({_identifier(column)})" for column in columns)
        return (
            f"SELECT {', '.join(expressions)} FROM {_identifier(table)} "
            f"GROUP BY GROUPING SETS ({sets})"
        )

    def probed(self, probes: Sequence[Probe], keys: Sequence[tuple[str, str]], limit: int) -> str:
        """The statement counting, of `limit` values taken of each probe, those in each key."""
        taken = " UNION ALL ".join(
            f'SELECT {place} AS "probe", "v", count(*) OVER () AS "taken" FROM (SELECT'
            f' CAST({probe.values} AS varchar) AS "v" FROM {_identifier(probe.table)}'
            f" TABLESAMPLE BERNOULLI ({probe.percent:.10f}) WHERE {probe.values} IS NOT NULL"
            f" LIMIT {limit})"
            for place, probe in enumerate(probes)
        )
        read = " UNION ALL ".join(
            f'SELECT {place} AS "key", CAST({_identifier(column)} AS varchar) AS "id"'
            f" FROM {_identifier(table)}"
            for place, (table, column) in enumerate(keys)
        )
        # An inner join, of the values taken on the right, so that they are what is held in memory,
        # and the keys are read past them; each row of them knows how many were taken.
        return (
            f'SELECT "probe", "key", "taken", count(*) FROM ({read}) "k"'
            f' JOIN ({taken}) "p" ON "p"."v" = "k"."id" GROUP BY "probe", "key", "taken"'
        )

    def covered(self, table: str, lookups: Sequence[Lookup]) -> str:
        """The statement counting, of each of `lookups` of `table`, its values found in its key."""
        values = ", ".join(
            f'CAST({lookup.values} AS varchar) AS "v{place}"'
            for place, lookup in enumerate(lookups)
        )
        joined = "".join(
            f' LEFT JOIN (SELECT CAST({_identifier(lookup.key)} AS varchar) AS "id"'
            f' FROM {_identifier(lookup.table)}) "k{place}" ON "t"."v{place}" = "k{place}"."id"'
            for place, lookup in enumerate(lookups)
        )
        counts = ", ".join(
            f'count("t"."v{place}"), count("k{place}"."id")' for place in range(len(lookups))
        )
        return f'SELECT {counts} FROM (SELECT {values} FROM {_identifier(table)}) "t"{joined}'

    def column(self, column: str) -> str:
        """The expression of the values of `column`."""
        return _identifier(column)

    def sentinels(self, column: str, kind: str, texts: Collection[str]) -> str:
        """The expression counting the values of `column` that are one of `texts`, as text."""
        return f"count_if({_among(column, kind, texts)})"

    def without(self, column: str, kind: str, texts: Collection[str]) -> str:
        """The expression of the values of `column`, null where a value is one of `texts`."""
        values = _identifier(column)
        if not texts:
            return values
        return f"CASE WHEN {_among(column, kind, texts)} THEN NULL ELSE {values} END"

    def grouping(self, column: str) -> str:
        """The expression that is 0 in the rows grouped by `column`, and 1 in the others."""
        return f"grouping({_identifier(column)})"

    def rows(self) -> str:
        """The expression counting the rows."""
        return "count(*)"

    def nulls(self, values: str) -> str:
        """The expression counting the nulls of `values`."""
        return f"count(*) - count({values})"

    def distinct(self, values: str) -> str:
        """The expression counting the distinct values of `values`, approximately."""
        return f"approx_distinct({values}, {_DISTINCT_ERROR})"

    def exactly_distinct(self, columns: Sequence[str]) -> str:
        """The expression counting the distinct values of `columns` together, exactly."""
        if len(columns) == 1:
            return f"count(DISTINCT {_identifier(columns[0])})"
        return f"count(DISTINCT ROW({', '.join(map(_identifier, columns))}))"

    def distinct_error(self) -> float:
        """The standard error of the distinct values `distinct` counts: half a percent."""
        return _DISTINCT_ERROR

    def smallest(self, values: str) -> str:
        """The expression of the smallest of `values`."""
        return f"min({values})"

    def largest(self, values: str) -> str:
        """The expression of the largest of `values`."""
        return f"max({values})"

    def shortest(self, values: str) -> str:
        """The expression of the length of the shortest of `values`."""
        return f"min(length({values}))"

    def longest(self, values: str) -> str:
        """The expression of the length of the longest of `values`."""
        return f"max(length({values}))"

    def matching(self, values: str, pattern: str) -> str:
        """The expression counting those of `values` that `pattern` matches whole."""
        # A value that cannot be cast, such as a JSON array, is no text, and matches nothing.
        text = f"trim(try_cast({values} AS varchar))"
        return f"count_if(regexp_like({text}, {_literal(f'^(?:{pattern})$')}))"

    def is_text(self, kind: str) -> bool:
        """Whether a column of the type `kind` holds texts: a `varchar` or a `char`."""
        return kind.startswith(_TEXTS)

    def is_ordered(self, kind: str) -> bool:
        """Whether the values of the type `kind` have an order: texts, numbers, times and a few."""
        return kind.startswith(_ORDERED)

    def has_text(self, kind: str) -> bool:
        """Whether Trino casts the values of the type `kind` to a text: all but a few."""
        return kind.startswith(_HAVE_TEXT)

    def identifies(self, kind: str) -> bool:
        """Whether the values of the type `kind` may identify rows: texts, exact numbers, days."""
        return kind.startswith(_IDENTIFYING)

    def is_surrogate(self, kind: str) -> bool:
        """Whether the type `kind` is one of the keys a database generates: whole numbers, UUIDs."""
        return _is_whole(kind) or kind.startswith(_SURROGATE)

    def is_unmistakable(self, kind: str) -> bool:
        """Whether values of the type `kind` are equal to those of another column by no chance."""
        return kind == "uuid"

    def is_same_family(self, kind: str, other: str) -> bool:
        """Whether values of `kind` and `other` are the same values where their texts are."""
        return _family(kind) == _family(other)


def _is_whole(kind: str) -> bool:
    """Whether the values of the type `kind` are whole numbers: decimals of no fraction as well."""
    return kind.startswith(_WHOLE) or _WHOLE_DECIMAL.fullmatch(kind) is not None


def _family(kind: str) -> str:
    """The family of the type `kind`, whose values are the same where their texts are.

    Texts are one, whole numbers another - decimals of no fraction among them -, decimals of a
    scale one each, and every other type a family of its own.
    """
    if kind.startswith(_TEXTS):
        return "text"
    if _is_whole(kind):
        return "whole"
    decimal = _DECIMAL.fullmatch(kind)
    if decimal is not None:
        return f"decimal of scale {decimal.group(1)}"
    return kind


def _among(column: str, kind: str, texts: Collection[str]) -> str:
    """The condition that a value of `column`, of the type `kind`, is one of `texts`, as text."""
    values = _identifier(column)
    day = f"CAST({values} AS date)" if kind.startswith(_MOMENTS) else values
    listed = ", ".join(_literal(text) for text in sorted(texts))
    return f"trim(try_cast({day} AS varchar)) IN ({listed})"


def _identifier(name: str) -> str:
    """`name` as a quoted identifier of SQL."""
    return '"' + name.replace('"', '""') + '"'


def _literal(text: str) -> str:
    """`text` as a string literal of SQL."""
    return "'" + text.replace("'", "''") + "'"
