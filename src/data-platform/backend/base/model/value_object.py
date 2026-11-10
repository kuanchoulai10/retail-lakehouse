"""Define the Pydantic ValueObject base class."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict

from base import enforce_max_depth

if TYPE_CHECKING:
    from collections.abc import Mapping


class ValueObject(BaseModel):
    """An immutable, self-contained descriptor with no conceptual identity.

    Two ValueObjects are equal when all of their fields are equal. They
    are frozen, so they are hashable and freely shareable. Validation is
    strict (no coercion: ``True`` is not an ``int``) and unknown keys are
    rejected, so an invalid value never gets built.

    A value read from or written to the outside world goes through
    ``from_primitives`` / ``to_primitives``: JSON-compatible primitives,
    enums as their values, durations as integer seconds under their
    ``*_seconds`` alias.

    Usage::

        class Money(ValueObject):
            amount: int
            currency: str
    """

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_by_name=True,
        validate_by_alias=True,
    )

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce flat hierarchy: concrete value objects extend ValueObject directly (max depth 1)."""
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, ValueObject, 1)

    @classmethod
    def from_primitives(cls, data: Mapping[str, Any]) -> Self:
        """Build from JSON-compatible primitives, validated in strict JSON mode."""
        return cls.model_validate_json(json.dumps(data))

    def to_primitives(self) -> dict[str, Any]:
        """Return JSON-compatible primitives keyed by alias."""
        return self.model_dump(mode="json", by_alias=True)
