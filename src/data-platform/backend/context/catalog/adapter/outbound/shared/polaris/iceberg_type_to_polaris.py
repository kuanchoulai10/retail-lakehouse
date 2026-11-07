"""Define the iceberg_type_to_polaris function."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from context.catalog.application.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

_PRIMITIVES = frozenset(
    {
        "boolean",
        "int",
        "long",
        "float",
        "double",
        "date",
        "time",
        "timestamp",
        "timestamptz",
        "timestamp_ns",
        "timestamptz_ns",
        "string",
        "uuid",
        "binary",
        "variant",
        "unknown",
    }
)
_PARAMETERIZED = re.compile(r"^(decimal\(\d+,\d+\)|fixed\[\d+\])$")
_REQUIRED = "required "
_STOP = ",<>"


class _Parser:
    """Recursive descent over the readable type syntax, assigning nested ids as it goes."""

    def __init__(self, text: str, next_id: Callable[[], int]) -> None:
        self._text = text
        self._pos = 0
        self._next_id = next_id

    def parse(self) -> str | dict[str, Any]:
        parsed = self._type()
        self._skip_spaces()
        if self._pos != len(self._text):
            raise self._error()
        return parsed

    def _error(self) -> ValidationError:
        return ValidationError(f"type {self._text!r} is not a valid Iceberg type")

    def _skip_spaces(self) -> None:
        while self._pos < len(self._text) and self._text[self._pos].isspace():
            self._pos += 1

    def _take(self, token: str) -> bool:
        self._skip_spaces()
        if self._text.startswith(token, self._pos):
            self._pos += len(token)
            return True
        return False

    def _expect(self, token: str) -> None:
        if not self._take(token):
            raise self._error()

    def _element(self) -> tuple[bool, str | dict[str, Any]]:
        required = self._take(_REQUIRED)
        return required, self._type()

    def _type(self) -> str | dict[str, Any]:
        if self._take("struct<"):
            return self._struct()
        if self._take("list<"):
            element_id = self._next_id()
            required, element = self._element()
            self._expect(">")
            return {"type": "list", "element-id": element_id, "element": element, "element-required": required}
        if self._take("map<"):
            key_id, value_id = self._next_id(), self._next_id()
            _, key = self._element()
            self._expect(",")
            required, value = self._element()
            self._expect(">")
            return {
                "type": "map",
                "key-id": key_id,
                "key": key,
                "value-id": value_id,
                "value": value,
                "value-required": required,
            }
        return self._primitive()

    def _struct(self) -> dict[str, Any]:
        fields: list[dict[str, Any]] = []
        if self._take(">"):
            return {"type": "struct", "fields": fields}
        while True:
            name = self._name()
            field_id = self._next_id()
            required, field_type = self._element()
            fields.append({"id": field_id, "name": name, "required": required, "type": field_type})
            if self._take(">"):
                return {"type": "struct", "fields": fields}
            self._expect(",")

    def _name(self) -> str:
        self._skip_spaces()
        end = self._text.find(":", self._pos)
        name = self._text[self._pos : end].strip() if end >= 0 else ""
        if not name or any(stop in name for stop in _STOP):
            raise self._error()
        self._pos = end + 1
        return name

    def _primitive(self) -> str:
        self._skip_spaces()
        start, depth = self._pos, 0
        while self._pos < len(self._text):
            char = self._text[self._pos]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0 and char in _STOP:
                break
            self._pos += 1
        name = re.sub(r"\s+", "", self._text[start : self._pos])
        if name not in _PRIMITIVES and not _PARAMETERIZED.match(name):
            raise self._error()
        return name


def iceberg_type_to_polaris(text: str, next_id: Callable[[], int]) -> str | dict[str, Any]:
    """Parse the readable type syntax into an Iceberg REST type, or raise ValidationError.

    A primitive becomes its name (``decimal(10, 2)`` is normalized to ``decimal(10,2)``); a
    nested type becomes its JSON object, each nested field, element, key and value taking its
    id from ``next_id``. An element without ``required`` is optional.
    """
    return _Parser(text, next_id).parse()
