"""Define the Pydantic EntityId base class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self

from pydantic import ConfigDict, RootModel, field_validator

from base._inheritance_guard import enforce_max_depth
from base._invariant_guarded_model import InvariantGuardedModel
from shared_kernel import new_prefixed_id, prefixed_id_pattern

if TYPE_CHECKING:
    import re


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
    ``<PREFIX>-<26 Crockford base32 characters>`` on every construction path,
    refusing anything else with ``InvariantViolation``, and ``new()`` mints a
    fresh one::

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
        cls._prefix_pattern = None if cls.PREFIX is None else prefixed_id_pattern(cls.PREFIX)

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
        return cls(new_prefixed_id(cls.PREFIX))

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
