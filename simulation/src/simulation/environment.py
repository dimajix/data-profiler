"""The database of the simulation environment, filled with the test data of profiles.

Its tables are created by Trino, from the types of the profile as Trino names them, and filled by
`COPY` in the PostgreSQL that holds them, which is much faster than inserting by Trino. Trino names
its tables and columns in lower case, in PostgreSQL as well. A failure of either is told by the
system, its endpoint and what was done; what the client said, which may hold a value, stays in the
cause of the error.
"""

import logging
from pathlib import Path
from random import Random
from types import TracebackType
from typing import Final, Self

import psycopg
from psycopg import sql
from requests import Session
from trino import dbapi
from trino.auth import BasicAuthentication
from trino.exceptions import Error as TrinoError
from trino.exceptions import HttpError

from data_profiler.profile import Profile, Table
from simulation import SimulationError
from simulation.data import rows

_logger = logging.getLogger(__name__)

# The environment as docker-compose.yml starts it.
_CATALOG: Final = "crm"
_TRINO: Final = "Trino at https://localhost:8443"
_TRINO_PORT: Final = 8443
_TRINO_USER: Final = "profiler"
_TRINO_PASSWORD: Final = "profiler"
_POSTGRES: Final = "PostgreSQL at localhost:5432"
_POSTGRES_CONNECTION: Final = "host=localhost port=5432 dbname=crm user=crm password=crm"

# The certificate of the simulated Trino, in the repository: the package is used from its
# workspace, installed in place, never on its own.
_CERTIFICATE: Final = Path(__file__).parents[2] / "trino" / "tls" / "trino.crt"


class Environment:
    """The database of the simulation environment, reached by Trino and PostgreSQL."""

    def __init__(self, trino: dbapi.Connection, postgres: psycopg.Connection) -> None:
        """Takes the connections to the Trino and the PostgreSQL of the environment.

        Args:
            trino: The connection to Trino.
            postgres: The connection to the PostgreSQL that holds the catalog `crm` of Trino.
        """
        self._trino = trino
        self._postgres = postgres

    @classmethod
    def connect(cls) -> Self:
        """Connects to the environment as docker-compose.yml starts it.

        It is reached on `localhost`, by the users of the environment, trusting its certificate
        and passing by any proxy, which would not reach it. Trino is asked first when a statement
        is sent to it.

        Returns:
            The environment.

        Raises:
            SimulationError: The PostgreSQL of the environment cannot be reached.
        """
        session = Session()
        session.trust_env = False
        session.verify = str(_CERTIFICATE)
        trino = dbapi.connect(  # type: ignore[no-untyped-call]  # the client has no annotations
            host="localhost",
            port=_TRINO_PORT,
            http_scheme="https",
            user=_TRINO_USER,
            auth=BasicAuthentication(_TRINO_USER, _TRINO_PASSWORD),
            http_session=session,
        )
        try:
            postgres = psycopg.connect(_POSTGRES_CONNECTION)
        except psycopg.Error as error:
            raise SimulationError(f"{_POSTGRES} cannot be reached") from error
        return cls(trino, postgres)

    def __enter__(self) -> Self:
        """Returns the environment, whose connections are closed at the end of the block."""
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Closes the connections to the environment."""
        self._trino.close()  # type: ignore[no-untyped-call]  # the client has no annotations
        self._postgres.close()

    def load(self, profile: Profile, seed: int = 0) -> None:
        """Creates the tables of `profile` in its schema of the catalog `crm`, and fills them.

        The schema is created if it does not exist. A table of the same name is replaced; the
        other tables of the schema are left as they are. All rows are generated before the first
        table is created, so that a profile whose data cannot be generated changes nothing.

        Args:
            profile: The profile whose tables are created.
            seed: The seed of the values; the same seed gives the same rows.

        Raises:
            SimulationError: The profile is of another catalog, its data cannot be generated, or
                Trino or PostgreSQL fails.
        """
        if profile.catalog != _CATALOG:
            raise SimulationError(
                f"the profile is of the catalog {profile.catalog}, the environment has {_CATALOG}"
            )
        random = Random(seed)
        tables = [(table, rows(table, random)) for table in profile.tables]
        schema = f"{_CATALOG}.{_quoted(profile.schema)}"
        self._query(f"CREATE SCHEMA IF NOT EXISTS {schema}", f"creating {profile.schema}")
        for table, data in tables:
            self._create(profile.schema, table)
            self._copy(profile.schema, table, data)
            _logger.info("Loaded %s.%s: %d rows", profile.schema, table.name, len(data))

    def count(self, schema: str, table: str) -> int:
        """The rows of a table in the catalog `crm`, as Trino counts them.

        Raises:
            SimulationError: Trino fails to count them.
        """
        answer = self._query(f"SELECT count(*) FROM {_name(schema, table)}", f"counting {table}")
        count = answer[0][0]
        if not isinstance(count, int):
            raise SimulationError(f"{_TRINO} counted {schema}.{table} as no number")
        return count

    def _create(self, schema: str, table: Table) -> None:
        """Creates `table` in `schema` by Trino, replacing a table of the same name."""
        columns = ", ".join(f"{_quoted(column.name)} {column.type}" for column in table.columns)
        name = _name(schema, table.name)
        self._query(f"DROP TABLE IF EXISTS {name}", f"dropping {schema}.{table.name}")
        self._query(f"CREATE TABLE {name} ({columns})", f"creating {schema}.{table.name}")

    def _copy(self, schema: str, table: Table, data: list[tuple[object, ...]]) -> None:
        """Fills `table` in `schema` with `data`, by `COPY` in PostgreSQL."""
        target = sql.Identifier(schema.lower(), table.name.lower())
        statement = sql.SQL("COPY {} FROM STDIN").format(target)
        try:
            with (
                self._postgres.transaction(),
                self._postgres.cursor() as cursor,
                cursor.copy(statement) as copy,
            ):
                for row in data:
                    copy.write_row(row)
        except psycopg.Error as error:
            raise SimulationError(f"{_POSTGRES} failed filling {schema}.{table.name}") from error

    def _query(self, statement: str, step: str) -> list[list[object]]:
        """Sends `statement` to Trino, and returns its rows once it has run.

        Raises:
            SimulationError: Trino fails at `step`.
        """
        try:
            cursor = self._trino.cursor()
            cursor.execute(statement)
            result: list[list[object]] = cursor.fetchall()
        except (TrinoError, HttpError) as error:
            raise SimulationError(f"{_TRINO} failed {step}") from error
        return result


def _name(schema: str, table: str) -> str:
    """The name of `table` in `schema` of the catalog `crm`, as Trino reads it."""
    return f"{_CATALOG}.{_quoted(schema)}.{_quoted(table)}"


def _quoted(name: str) -> str:
    """`name` as a quoted identifier of Trino."""
    return '"' + name.replace('"', '""') + '"'
