"""Documents: the YAML files a person reads and writes, each of a format of its own.

A document is of a `Format`, which reads and writes it: it holds the fields of the class of its
format, checked by pydantic, and the version of its format in the field `format`; one with a field
missing, unknown or of the wrong type is refused. The field `format` is the document's own: a class
a document holds has none. A field that has its default is not written: a document holds what
differs from the defaults. The validators of a document share a context, a dict made anew for each
document read, by which a field is checked against another that holds what it names - in the same
document, or in another one, whose reader gives what it holds to begin the context with. The profile
is made of such documents, and the configuration of a project is one.

Several documents of a format may be read as one, as the overrides of a project are: each is read by
itself, then their maps are merged key by key, and a field two of them give is refused, whatever
each gives, so that the order of the documents does not matter. The fields are merged as the
documents give them, before the classes take their defaults, which no longer tell a field given as
its default from one not given.

A field of such documents is set by `Format.amend`, in the document that gives it. As a person
writes them, the comments, the order and the writing of all else stay as they are, by a round trip
of `ruamel.yaml`, which is used for that alone: what a document holds is always read by PyYAML, as
the document amended is before it is written.

The version of a format has a major and a minor part. The major version is raised with a change to
the fields of the classes of the format that is incompatible, and the minor version set to 0: a
field added that is required, a field renamed or removed, a default changed - a default is not
written, so that a document of the version before would be read with another value, unseen -, or
the type or the meaning of a field changed. The minor version is raised with a change that is
compatible: a field added that is optional, a required field made optional, or a value added to
those a field takes - a semantic type of the tool, which a match names -, which a tool older than
the document would refuse. A document of the
major version read and of its minor version or an older one is read, what it lacks taken by its
defaults; one of a newer minor version is refused, as its fields are unknown to the tool, and one
of another major version as well.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Final, TextIO

from pydantic import TypeAdapter, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError as RoundTripError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, SingleQuotedScalarString
from yaml import YAMLError, safe_dump, safe_load

from data_profiler.files import write_whole

# A version as a document writes it, a string: YAML would read `13.10` as the number `13.1`.
_VERSION: Final = re.compile(r"(\d+)\.(\d+)")


@dataclass(frozen=True)
class Version:
    """The version of a format, as the module docs say when each of its parts is raised."""

    major: int
    minor: int

    def __str__(self) -> str:
        """The version as a document writes it, `13.1`."""
        return f"{self.major}.{self.minor}"


class DocumentError(Exception):
    """A document that cannot be read or written: its file, and what is wrong with it."""


class Format[T]:
    """The format of one kind of document: the class it holds, and the version of its fields.

    Attributes:
        root: The class a document of the format holds.
        version: The version of the format, raised as the module docs say.
    """

    def __init__(self, root: type[T], version: Version) -> None:
        """Takes the class a document of the format holds, and the version of the format."""
        self.root = root
        self.version = version
        self._adapter = TypeAdapter(root)

    def read(self, path: Path, context: Mapping[str, object] | None = None) -> T:
        """The YAML document in `path`, of this format or of an older minor version of it.

        What a document of an older minor version lacks takes its default. A version is written as
        a string, `"13.1"`; a plain number, `13`, is read as `"13.0"`.

        Args:
            path: The file of the document.
            context: What the context of its validators begins with, of another document; nothing
                where none is given.

        Returns:
            What the document holds.

        Raises:
            DocumentError: The file cannot be read, is no YAML, holds no fields, names no version
                of a format, is of another major version or of a newer minor version, or a field is
                missing, unknown or of the wrong type.
        """
        return self._validated(self._content(path), str(path), context)

    def read_merged(self, paths: Sequence[Path]) -> T:
        """The YAML documents in `paths`, each read as `read` reads it, merged into one.

        Their fields are merged key by key where both give a map, so that one document may give some
        fields of an entry and another the others; a field given in two of them is refused, whatever
        either gives, so that what is read does not depend on the order of the documents. No
        documents merge into the empty one.

        Args:
            paths: The files of the documents.

        Returns:
            What the documents hold, merged.

        Raises:
            DocumentError: A document cannot be read as `read` reads it, naming its file; a field is
                given in two documents, naming the field and both files; or the documents merged
                are refused as `read` refuses a document, naming them all.
        """
        merged: dict[str, Any] = {}
        givers: dict[tuple[object, ...], Path] = {}
        for path in paths:
            content = self._content(path)
            # Each document is checked by itself first, so that a field of the wrong type is named
            # with its file: the merged document no longer tells which file gave it.
            self._validated(content, str(path), None)
            _merge(merged, content, path, (), givers)
        return self._validated(merged, ", ".join(str(path) for path in paths), None)

    def write(self, path: Path, value: T) -> None:
        """Writes `value` to `path` as a YAML document of this format, whole or not at all.

        Args:
            path: The file of the document.
            value: What the document is to hold.

        Raises:
            DocumentError: The file cannot be written.
        """
        content = {
            "format": str(self.version),
            **self._adapter.dump_python(value, mode="json", exclude_defaults=True),
        }
        try:
            text = safe_dump(content, sort_keys=False, allow_unicode=True)
            write_whole(path, text.encode("utf-8"))
        except OSError as error:
            raise DocumentError(f"{path} cannot be written: {error.strerror}") from error

    def amend(
        self, paths: Sequence[Path], field: Sequence[str], value: object, otherwise: Path
    ) -> None:
        """Sets `field` where it is given, else in the first document of its entry, or `otherwise`.

        The comments, the order and the writing of what is not set stay as the documents have them,
        with three exceptions in the document changed: the lists written over several lines, and
        the maps, take one indentation; a null is written empty; and a new field or entry comes
        last in its map, so that a comment that follows a text or a list written over several lines
        comes before it. A list given is changed in place, so that it stays written as it was; a
        new list is written in one line, as a person writes one.

        Args:
            paths: The files of the documents, which `read_merged` reads; a field is given in one.
            field: The keys of the field; its entry is the map whose key the last of them is.
            value: What the field is to hold, a text, a number or a list of them.
            otherwise: The file a field goes to whose entry no document of `paths` gives; made, with
                its directory and the version of this format, where it is not there.

        Raises:
            DocumentError: A document cannot be read, is no YAML or holds no fields, a key on the
                way to the field holds no map, or one or the list it is an anchor shares, the
                document changed would be refused as `read` refuses one, or the file cannot be
                written.
        """
        documents = {
            path: _loaded(path, _round_trip().load)
            for path in ([*paths, otherwise] if otherwise.is_file() else paths)
        }
        entries = {
            path: entry
            for path, document in documents.items()
            if (entry := _entry(document, field[:-1])) is not None
        }
        target = next((p for p, entry in entries.items() if field[-1] in entry), None)
        target = target or next(iter(entries), otherwise)
        document = documents.get(target)
        if document is None:
            document = CommentedMap(format=DoubleQuotedScalarString(str(self.version)))
        _set(document, field, value, target)
        written = StringIO()
        _round_trip().dump(document, written)
        text = written.getvalue()
        try:
            content = safe_load(text)
        except YAMLError as error:
            raise DocumentError(f"{target} is no YAML: {error}") from error
        self._validated(self._fields(content, target), str(target), None)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_whole(target, text.encode("utf-8"))
        except OSError as error:
            raise DocumentError(f"{target} cannot be written: {error.strerror}") from error

    def _content(self, path: Path) -> dict[str, Any]:
        """The fields of the document in `path`, once its version is found to be read."""
        return self._fields(_loaded(path, safe_load), path)

    def _fields(self, content: dict[str, Any], path: Path) -> dict[str, Any]:
        """`content` of the document in `path` without its version, once it is found to be read."""
        found = content.pop("format", None)
        if found is None:
            raise DocumentError(f"{path} names no format")
        given = _version(path, found)
        if given.major != self.version.major:
            raise DocumentError(
                f"{path} is of format {given}, of another major version than the format"
                f" {self.version} that is read"
            )
        if given.minor > self.version.minor:
            raise DocumentError(
                f"{path} is of format {given}, newer than the format {self.version} that is read:"
                " the tool is older than the document"
            )
        return content

    def _validated(
        self, content: dict[str, Any], source: str, context: Mapping[str, object] | None
    ) -> T:
        """What the fields `content` of the documents named `source` hold, checked by pydantic."""
        try:
            return self._adapter.validate_python(
                content, extra="forbid", context=dict(context or {})
            )
        except ValidationError as error:
            problems = "; ".join(_problem(detail) for detail in error.errors())
            raise DocumentError(f"{source}: {problems}") from error


def _loaded(path: Path, load: Callable[[TextIO], Any]) -> dict[Any, Any]:
    """The map the YAML document in `path` holds, read by `load`.

    Raises:
        DocumentError: The file cannot be read, is no YAML, or holds no fields.
    """
    try:
        with path.open(encoding="utf-8") as file:
            content = load(file)
    except OSError as error:
        raise DocumentError(f"{path} cannot be read: {error.strerror}") from error
    except (YAMLError, RoundTripError) as error:
        raise DocumentError(f"{path} is no YAML: {error}") from error
    if not isinstance(content, dict):
        raise DocumentError(f"{path} holds no fields")
    return content


def _round_trip() -> YAML:
    """A reader and writer that keeps what a person wrote, and folds no line of it."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=2, offset=0)
    return yaml


def _entry(document: dict[Any, Any], keys: Sequence[str]) -> dict[Any, Any] | None:
    """The map the keys `keys` lead to in `document`, or None where they lead to none."""
    found: object = document
    for key in keys:
        found = found.get(key) if isinstance(found, dict) else None
    return found if isinstance(found, dict) else None


def _set(document: dict[Any, Any], field: Sequence[str], value: object, path: Path) -> None:
    """Sets the field `field` of `document`, the one in `path`, to `value`, as `amend` says."""
    for key in field[:-1]:
        document = document.setdefault(_text(key), CommentedMap())
        # An anchor is one map at each of its aliases, which would all change.
        if not isinstance(document, CommentedMap) or document.yaml_anchor() is not None:
            raise _unsettable(field, path)
    styled = _styled(value)
    given = document.get(field[-1])
    if isinstance(given, CommentedSeq) and isinstance(styled, CommentedSeq):
        if given.yaml_anchor() is not None:
            raise _unsettable(field, path)
        _replace_items(given, styled)
    else:
        document[_text(field[-1])] = styled


def _unsettable(field: Sequence[str], path: Path) -> DocumentError:
    """The error of the field `field` of the document in `path`, which `amend` cannot set."""
    return DocumentError(
        f"{path}: {_field(field)} cannot be set, as what holds it is no map or an anchor shares it"
    )


def _replace_items(given: CommentedSeq, items: CommentedSeq) -> None:
    """Makes the list `given` hold `items`, what is at the same place in it left as it was.

    What follows a list written over several lines is a comment of its last item, and stays at its
    end, in place of a comment of the item that comes to be last.
    """
    following = given.ca.items.pop(len(given) - 1, None)
    for index, item in enumerate(items):
        if index == len(given):
            given.append(item)
        elif given[index] != item:
            given[index] = item
    del given[len(items) :]
    if following is not None and items:
        given.ca.items[len(items) - 1] = following


def _styled(value: object) -> object:
    """`value` as the round trip is to write it: a list in one line, a text as `_text` says."""
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, Sequence):
        items = CommentedSeq([_styled(item) for item in value])
        items.fa.set_flow_style()
        return items
    return value


def _text(text: str) -> str:
    """`text`, quoted where PyYAML would otherwise read it as anything but a text.

    The round trip writes YAML 1.2, in which `no` is a text; PyYAML, which reads every document,
    reads YAML 1.1, in which it is a boolean, and quotes such a text where it writes one.
    """
    quoted = safe_dump(text, allow_unicode=True)[0] in "'\""
    return SingleQuotedScalarString(text) if quoted else text


def _merge(
    merged: dict[Any, Any],
    content: dict[Any, Any],
    path: Path,
    at: tuple[object, ...],
    givers: dict[tuple[object, ...], Path],
) -> None:
    """Merges `content` of the document in `path` into `merged`, the map at the field `at`.

    Args:
        merged: The fields merged so far, changed in place.
        content: The fields of the document.
        path: The file of the document.
        at: The keys of the field that is the map `merged`, none for the document.
        givers: The file that gave each field first, by its keys, changed in place.

    Raises:
        DocumentError: A field of `content` is given in a document merged before.
    """
    for key, value in content.items():
        field = (*at, key)
        if key not in merged:
            givers[field] = path
            # A map is merged into one of its own, never taken: the aliases of an anchor of YAML are
            # one dict, which a later document would otherwise extend at each of them.
            if isinstance(value, dict):
                merged[key] = {}
                _merge(merged[key], value, path, field, givers)
            else:
                merged[key] = value
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            _merge(merged[key], value, path, field, givers)
        else:
            raise DocumentError(f"{_field(field)} is given in {givers[field]} and in {path}")


def _version(path: Path, found: object) -> Version:
    """The version of a format the field `format` of the document in `path` gives as `found`."""
    if type(found) is int:
        return Version(found, 0)
    if isinstance(found, str) and (parts := _VERSION.fullmatch(found)):
        return Version(int(parts[1]), int(parts[2]))
    raise DocumentError(
        f'{path} names the format {found!r}, which is no version of one, written as "1.0"'
    )


def _problem(detail: Any) -> str:
    """The field a detail of a `ValidationError` is about, and what is wrong with it."""
    return f"{_field(detail['loc'])}: {detail['msg']}"


def _field(keys: Sequence[object]) -> str:
    """The field of a document the keys `keys` lead to, as a message names it: `parts.0.name`."""
    return ".".join(str(key) for key in keys)
