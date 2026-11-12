"""The data contract: the profile as a document of the Open Data Contract Standard, template odcs.

A `Contract` writes the profile, the overrides laid over it, as one document of ODCS, of version
3.2.0, `contract.odcs.yaml`: what the project gives of the contract - its identifier, version, name,
domain and tenant -, the status `draft`, the description of the database the overrides give as its
purpose, the server of the environment, and a schema object of each table and a property of each
column, under their original names, their harmonized names as their business names.

The contract is an inventory of what was observed, which experts are to extend and rework into what
is binding: what holds of every row of the profile is written as a rule - a column of no nulls is
required, and has none of the sentinels its type can hold where none were found, a key of one column
is unique, a key of two has no duplicates, the values of an enumeration are those it takes, a
semantic type every value of a column of texts matches gives the pattern of its detector, of which
none is invalid, spaces at either end aside as the database matched it, and the lengths and the
range of the values are their bounds -, each taking the sentinels found as values, which they are
counted without, so that the contract holds of the rows it was observed of, and the experts see the
sentinels to forbid; but nothing counted is: no number of rows, no share of nulls, no coverage of a
reference. The references are relationships of the columns to their keys, but those of a column of
lists, which refers by the values of its lists; the reference candidates, of which none is
preferred, the column groups, the column dependencies and the entities are left out. A column of
lists is written as one of its texts. What the profile withholds of a column of a sensitivity - its
range and its values - the contract does not hold either: it holds what the profile holds, and
nothing of the workspace.
"""

import math
import re
from collections.abc import Mapping
from datetime import date
from typing import Any, Final

from yaml import safe_dump

from data_profiler.detect import UUID, Sensitivity, sentinels
from data_profiler.export import Template
from data_profiler.glossary import Glossary
from data_profiler.overrides import Overrides
from data_profiler.profile import Column, Profile, Range, Table
from data_profiler.project import ContractSettings
from data_profiler.source import Dialect, Location

# The file of the contract, in the directory of the template.
_FILE: Final = "contract.odcs.yaml"

# The version of ODCS the contract is of, and the status it is written in: a draft, an inventory
# for experts to make binding.
_API_VERSION: Final = "v3.2.0"
_STATUS: Final = "draft"

# The logical types whose values are numbers, and those whose ranges ODCS takes as bounds.
_NUMBERS: Final = ("integer", "number")
_RANGED: Final = (*_NUMBERS, "date", "timestamp", "time")

# A whole number, as a value of the profile writes it.
_WHOLE: Final = re.compile(r"[+-]?[0-9]+")

type _Document = dict[str, object]
"""A part of the document of the contract, as YAML writes it."""


class Contract(Template):
    """The data contract: the profile as one document of ODCS, `contract.odcs.yaml`, template odcs.

    It is made for the environment whose profile it writes, by its server.
    """

    name = "odcs"

    def __init__(
        self, settings: ContractSettings, server: str, location: Location, dialect: Dialect
    ) -> None:
        """Takes what the project gives of the contract, and the environment it is of.

        Args:
            settings: What the project gives of the contract, which the database does not tell.
            server: The name of the server, that of the environment.
            location: Where the schema of the environment is reached.
            dialect: The dialect of its database, which tells the types of the contract.
        """
        self._settings = settings
        self._server = server
        self._location = location
        self._dialect = dialect

    def files(self, profile: Profile, overrides: Overrides) -> Mapping[str, bytes]:
        """The contract, `contract.odcs.yaml`, of `profile`, the overrides laid over it.

        Args:
            profile: The profile, the overrides laid over it already.
            overrides: The overrides of the project, which the profile laid over holds all the
                contract shows of.

        Returns:
            The contract, as YAML in UTF-8, by the name of its file.
        """
        glossary = Glossary(profile.glossary)
        document: _Document = {
            "apiVersion": _API_VERSION,
            "kind": "DataContract",
            "id": self._settings.id,
            "version": self._settings.version,
            "status": _STATUS,
            **_present(
                name=self._settings.name,
                domain=self._settings.domain,
                tenant=self._settings.tenant,
            ),
        }
        if profile.description is not None:
            document["description"] = {"purpose": profile.description}
        document["servers"] = [
            {
                "server": self._server,
                "type": self._dialect.server_type,
                "host": self._location.host,
                "port": self._location.port,
                "catalog": self._location.catalog,
                "schema": self._location.schema,
            }
        ]
        document["schema"] = [self._object(table, glossary) for table in profile.tables]
        text = safe_dump(document, sort_keys=False, allow_unicode=True, width=100)
        return {_FILE: text.encode("utf-8")}

    def _object(self, table: Table, glossary: Glossary) -> _Document:
        """The schema object of `table`: its properties, and the rule of each key of two columns."""
        document: _Document = {
            "name": table.name,
            "physicalName": table.name,
            "physicalType": "table",
            "logicalType": "object",
            **_present(businessName=glossary.harmonized(table), description=table.description),
            "properties": [self._property(table, column, glossary) for column in table.columns],
        }
        quality = [
            {"metric": "duplicateValues", "arguments": {"properties": list(key)}, "mustBe": 0}
            for key in table.keys
            if len(key) > 1
        ]
        if quality:
            document["quality"] = quality
        return document

    def _property(self, table: Table, column: Column, glossary: Glossary) -> _Document:
        """The property of `column` of `table`, with the rules of what holds of every row."""
        logical = self._dialect.logical_type(column.type)
        document: _Document = {
            "name": column.name,
            "physicalName": column.name,
            **_present(
                businessName=glossary.harmonized(column),
                description=column.description,
                logicalType=logical,
            ),
            "physicalType": column.type,
            **_keyed(table, column),
        }
        if column.sensitivity is not Sensitivity.NONE:
            document["classification"] = column.sensitivity.value
        if column.matches:
            document["tags"] = [match.type.name for match in column.matches]
        if column.values:
            values = [*column.values, *column.statistics.sentinels]
            document["enum"] = [{"value": _bound(value.value, logical)} for value in values]
        options = _options(column, logical)
        if options:
            document["logicalTypeOptions"] = options
        quality = [*self._missing(column), *self._invalid(column)]
        if quality:
            document["quality"] = quality
        return document

    def _missing(self, column: Column) -> list[_Document]:
        """The rule that `column` holds no sentinels, where it holds no nulls and none were found.

        Its sentinels are those given of it, else those of the tool, of them those its type can
        hold, as the dialect tells - a rule of a number or a UUID against `N/A`, which it cannot
        hold, would say nothing.
        """
        statistics = column.statistics
        if statistics.nulls or statistics.sentinels:
            return []
        missing = sorted(self._dialect.held(column.type, sentinels(column.sentinels)))
        if not missing:
            return []
        return [{"metric": "missingValues", "arguments": {"missingValues": missing}, "mustBe": 0}]

    def _invalid(self, column: Column) -> list[_Document]:
        """The rule of each semantic type every value of `column` of texts is of: none invalid.

        Its pattern is that of the detector of the type, which every value matches whole, spaces
        at either end aside, as the database matched it, or one of the sentinels found, which the
        type is counted without; a column of another type, whose values the pattern says nothing
        of beyond their type, has none.
        """
        if not self._dialect.is_text(column.type):
            return []
        found = "".join(f"|{_escaped(value.value)}" for value in column.statistics.sentinels)
        return [
            {
                "metric": "invalidValues",
                "arguments": {
                    "pattern": rf"^\s*(?:{match.type.detector.pattern.pattern}{found})\s*$"
                },
                "mustBe": 0,
            }
            for match in column.matches
            if match.table == 1
        ]


def _keyed(table: Table, column: Column) -> _Document:
    """What `column` is of `table`: required, unique, of its primary key, and its reference."""
    document: _Document = {}
    if column.statistics.nulls == 0:
        document["required"] = True
    if (column.name,) in table.keys:
        document["unique"] = True
    if table.primary_key is not None and column.name in table.primary_key.columns:
        document["primaryKey"] = True
        document["primaryKeyPosition"] = table.primary_key.columns.index(column.name) + 1
    reference = table.reference(column.name)
    # A column of lists refers by the values of its lists, which it is not written as.
    if reference is not None and column.items is None:
        document["relationships"] = [{"to": f"{reference.table}.{reference.key}"}]
    return document


def _options(column: Column, logical: str | None) -> _Document:
    """The bounds of the values of `column` of the logical type `logical`, and their format.

    The lengths of its texts bound a string, its range a number or a time - none where it is
    withheld -, each widened to the sentinels found, which they are counted without, those of the
    range that are values of its type; a UUID every value of the table is of, and no sentinel, is
    of the format `uuid`.
    """
    statistics = column.statistics
    found = [value.value for value in statistics.sentinels]
    options: _Document = {}
    if not found and any(match.type == UUID and match.table == 1 for match in column.matches):
        options["format"] = "uuid"
    if statistics.lengths is not None and logical == "string":
        lengths = [statistics.lengths.shortest, statistics.lengths.longest, *map(len, found)]
        options["minLength"] = min(lengths)
        options["maxLength"] = max(lengths)
    if statistics.range is not None and logical in _RANGED:
        options |= _bounds(statistics.range, found, logical)
    return options


def _bounds(ends: Range, found: list[str], logical: str) -> _Document:
    """The minimum and maximum of `ends`, as `logical` writes them, widened to the sentinels found.

    The sentinels that are values of the type widen them; an end withheld is none.
    """
    # Numbers, or texts of times, which compare alike, as the type of the column is one of them.
    widening: list[Any] = [_bound(text, logical) for text in found if _is_of(text, logical)]
    bounds: _Document = {}
    if ends.smallest is not None:
        bounds["minimum"] = min([_bound(ends.smallest, logical), *widening])
    if ends.largest is not None:
        bounds["maximum"] = max([_bound(ends.largest, logical), *widening])
    return bounds


def _escaped(text: str) -> str:
    """`text` as a regular expression of itself, its characters of a meaning escaped."""
    return re.sub(r"[\\^$.|?*+()\[\]{}]", lambda found: f"\\{found[0]}", text)


def _present(**fields: object) -> _Document:
    """`fields`, but those of no value, which a contract leaves out."""
    return {name: value for name, value in fields.items() if value is not None}


def _is_of(text: str, logical: str) -> bool:
    """Whether `text` is a value of the logical type `logical`: a number, a date, or neither."""
    if logical in _NUMBERS:
        return _bound(text, logical) is not text
    if logical in ("date", "timestamp"):
        try:
            date.fromisoformat(text)
        except ValueError:
            return False
        return True
    return False


def _bound(text: str | None, logical: str | None) -> object:
    """`text`, a value of the profile, as the logical type `logical` writes it; None where withheld.

    A number is written as one, where it is a finite one, other values as their texts: a whole
    number as an integer, so that a long one of a decimal keeps its digits.
    """
    if text is None or logical not in _NUMBERS:
        return text
    if _WHOLE.fullmatch(text):
        return int(text)
    if logical == "integer":
        return text
    try:
        number = float(text)
    except ValueError:
        return text
    return number if math.isfinite(number) else text
