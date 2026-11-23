"""Define the Pydantic EntityId base class."""

from __future__ import annotations

import re
import uuid
from typing import Any, ClassVar, Self

from pydantic import ConfigDict, RootModel, field_validator

from base._inheritance_guard import enforce_max_depth
from base._invariant_guarded_model import InvariantGuardedModel

_BASE32_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
_PREFIX = re.compile(r"[a-z]{2,8}")
_SUFFIX = "[0-7][0-9a-hjkmnp-tv-z]{25}"
_ANY_PREFIXED_ID = re.compile(rf"{_PREFIX.pattern}-{_SUFFIX}")


def _encode_base32(value: int) -> str:
    """Encode a 128-bit integer as 26 lowercase base32 characters, big-endian, as the TypeID specification does.

    The 130 bits of 26 characters hold the 128 bits with two leading zero bits, so the first character is 0 to 7.
    """
    return "".join(_BASE32_ALPHABET[(value >> shift) & 0b11111] for shift in range(125, -1, -5))


def _prefixed_id_pattern(prefix: str) -> re.Pattern[str]:
    """Return the pattern of ``<prefix>-<26 base32 characters>``; raise ``ValueError`` for a malformed prefix."""
    if not _PREFIX.fullmatch(prefix):
        raise ValueError(f"prefix must be 2 to 8 lowercase letters, got {prefix!r}")
    return re.compile(rf"{prefix}-{_SUFFIX}")


class EntityId(InvariantGuardedModel, RootModel[str]):
    """A typed identifier for an Entity.

    Wraps a raw string in a distinct type so that ids of different Entity
    kinds cannot be mixed up: ``OrderId("1") != UserId("1")``. Built
    positionally, frozen, hashable and strict (only a ``str`` is accepted;
    anything else raises ``InvariantViolation``).

    Subclass per Entity type::

        class OrderId(EntityId):
            pass

    An id kind that this platform mints declares its ``PREFIX`` (2 to 8
    lowercase letters, docs/adr/0011). It then accepts only
    ``<PREFIX>-<26 base32 characters>`` on every construction path, refusing
    anything else with ``InvariantViolation``, and ``new()`` mints a fresh one,
    a UUIDv7 in the TypeID specification's base32, so ids sort by time::

        class RunId(EntityId):
            PREFIX: ClassVar[str | None] = "mr"

    ``PREFIX`` is a class variable, not a field: the id still dumps, serializes
    and prints as its bare string. Without a ``PREFIX`` an id accepts any string.
    """

    PREFIX: ClassVar[str | None] = None
    _prefix_pattern: ClassVar[re.Pattern[str] | None] = None

    model_config = ConfigDict(frozen=True, strict=True)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce a flat hierarchy (max depth 1) and compile the pattern of a declared ``PREFIX``.

        A ``PREFIX`` that is not 2 to 8 lowercase letters raises ``ValueError`` here, when the class is defined.
        """
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, EntityId, 1)
        cls._prefix_pattern = None if cls.PREFIX is None else _prefixed_id_pattern(cls.PREFIX)

    @field_validator("root")
    @classmethod
    def _has_the_declared_prefix(cls, value: str) -> str:
        """Refuse a value not of the shape ``<PREFIX>-<26 base32 characters>`` when ``PREFIX`` is set."""
        if cls._prefix_pattern is not None and not cls._prefix_pattern.fullmatch(value):
            raise ValueError(f"{cls.__name__} must look like {cls.PREFIX}-<26 base32 characters>")
        return value

    @classmethod
    def new(cls) -> Self:
        """Mint a fresh id of this kind; raise ``TypeError`` when the kind declares no ``PREFIX``."""
        if cls.PREFIX is None:
            raise TypeError(f"{cls.__name__} has no PREFIX, so it cannot mint a new id")
        return cls(f"{cls.PREFIX}-{_encode_base32(uuid.uuid7().int)}")

    @staticmethod
    def is_shaped_like_an_id(text: str) -> bool:
        """Tell whether ``text`` is shaped like an id of any prefix: ``<2-8 lowercase letters>-<26 base32 characters>``.

        For a rule that refuses whatever could be mistaken for an id (a name, say), whichever kind it would be.
        """
        return _ANY_PREFIXED_ID.fullmatch(text) is not None

    @property
    def value(self) -> str:
        """Return the raw identifier string."""
        return self.root

    @property
    def suffix(self) -> str:
        """Return the 26 characters after ``<PREFIX>-``; raise ``TypeError`` when the kind declares no ``PREFIX``."""
        if self.PREFIX is None:
            raise TypeError(f"{type(self).__name__} has no PREFIX, so its ids have no suffix")
        return self.root.removeprefix(f"{self.PREFIX}-")

    def __str__(self) -> str:
        """Return the raw identifier string."""
        return self.root
