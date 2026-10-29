"""The database the tool reads: a schema of it, its tables and columns, and the queries sent to it.

A `Source` sends queries and nothing else, and lists the tables and columns of its schema. Every
statement it sends is written by its `Dialect`: whole, where it lists them, and of the building
blocks the dialect offers, where another part counts what the tables hold. A failure is told by the
database, its endpoint and what was done; what the database said, which may hold a value of it,
stays in the cause of the error. Trino is reached by HTTPS, whose certificates and proxies come from
the environment, as `requests` reads them: `REQUESTS_CA_BUNDLE` for a certificate of a CA of one's
own, `NO_PROXY` for a database a proxy does not reach.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
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
_FORM: Final = "trino://user@host:port/catalog/schema"

# The types of Trino whose values are texts, by how their names begin.
_TEXTS: Final = ("varchar", "char")

# The standard error of the distinct values Trino counts: half a percent, against its default of
# 2.3, so that keys and enums can be told by them, for about 64 KB of memory per column.
_DISTINCT_ERROR: Final = 0.005


class SourceError(Exception):
    """A failure of the database: the database by its endpoint, and what was done."""


class Dialect(ABC):
    """The SQL of one kind of database: the statements and expressions the tool sends.

    Its building blocks take the names of tables and columns as they are, and quote them.
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
    def rows(self) -> str:
        """The expression counting the rows."""

    @abstractmethod
    def nulls(self, column: str) -> str:
        """The expression counting the nulls of `column`."""

    @abstractmethod
    def distinct(self, column: str) -> str:
        """The expression counting the distinct values of `column`, approximately."""

    @abstractmethod
    def shortest(self, column: str) -> str:
        """The expression of the length of the shortest value of `column`."""

    @abstractmethod
    def longest(self, column: str) -> str:
        """The expression of the length of the longest value of `column`."""

    @abstractmethod
    def is_text(self, kind: str) -> bool:
        """Whether a column of the type `kind`, as the database names it, holds texts."""


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


def connect(url: str, password: str) -> Source:
    """Connects to the schema `url` names.

    Args:
        url: The schema, as `trino://user@host:port/catalog/schema`; the port is 443 if none is
            given. Trino is reached by HTTPS.
        password: The password of the user.

    Returns:
        The source; the database is reached first when a statement is sent to it.

    Raises:
        SourceError: The URL is not of Trino, holds a password, a query or a fragment, or lacks
            the user, the host, the catalog or the schema. The message never repeats the URL,
            which may hold a password.
    """
    parts = urlsplit(url)
    if parts.scheme != "trino":
        raise SourceError(f"only a URL of Trino is read, {_FORM}, not of {parts.scheme or 'none'}")
    if parts.password is not None:
        raise SourceError("the URL holds a password, which is given apart from it")
    if parts.query or parts.fragment:
        raise SourceError(
            f"the URL has a query or a fragment, which a URL of Trino has not: {_FORM}"
        )
    try:
        port = parts.port or _PORT
    except ValueError as error:
        raise SourceError("the port of the URL is no number from 0 to 65535") from error
    path = parts.path.strip("/").split("/")
    if not parts.username or not parts.hostname or len(path) != 2 or not all(path):
        raise SourceError(f"the URL lacks user, host, catalog or schema: {_FORM}")
    catalog, schema = path
    connection: Connection = dbapi.connect(  # type: ignore[no-untyped-call]  # no annotations
        host=parts.hostname,
        port=port,
        http_scheme="https",
        user=parts.username,
        auth=BasicAuthentication(parts.username, password),
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

    def rows(self) -> str:
        """The expression counting the rows."""
        return "count(*)"

    def nulls(self, column: str) -> str:
        """The expression counting the nulls of `column`."""
        return f"count(*) - count({_identifier(column)})"

    def distinct(self, column: str) -> str:
        """The expression counting the distinct values of `column`, approximately."""
        return f"approx_distinct({_identifier(column)}, {_DISTINCT_ERROR})"

    def shortest(self, column: str) -> str:
        """The expression of the length of the shortest value of `column`."""
        return f"min(length({_identifier(column)}))"

    def longest(self, column: str) -> str:
        """The expression of the length of the longest value of `column`."""
        return f"max(length({_identifier(column)}))"

    def is_text(self, kind: str) -> bool:
        """Whether a column of the type `kind` holds texts: a `varchar` or a `char`."""
        return kind.startswith(_TEXTS)


def _identifier(name: str) -> str:
    """`name` as a quoted identifier of SQL."""
    return '"' + name.replace('"', '""') + '"'


def _literal(text: str) -> str:
    """`text` as a string literal of SQL."""
    return "'" + text.replace("'", "''") + "'"
