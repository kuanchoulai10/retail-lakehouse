"""Define the Pydantic Entity base class."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from base import enforce_max_depth
from base.model.entity_id import EntityId
from base.model.validated_copy import validated_copy


class Entity[ID: EntityId](BaseModel):
    """An object with a distinct identity that persists through state changes.

    Two Entities are equal when they are of one class and share the same
    ``id``, even if every other field differs; hashing follows the id.
    State may change, and every assignment is validated, strictly.

    Usage::

        class UserId(EntityId):
            pass

        class User(Entity[UserId]):
            name: str
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        validate_assignment=True,
        validate_by_name=True,
        validate_by_alias=True,
    )

    _depth_base: ClassVar[bool] = True

    id: ID  # noqa: A003

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce a flat hierarchy (max depth 1) below the nearest depth base.

        The depth base is the nearest ancestor that declares ``_depth_base``
        in its own body: ``Entity`` for entities, ``AggregateRoot`` for
        aggregates.
        """
        super().__pydantic_init_subclass__(**kwargs)
        base = next(parent for parent in cls.__mro__[1:] if "_depth_base" in vars(parent))
        enforce_max_depth(cls, base, 1)

    def __eq__(self, other: object) -> bool:
        """Compare equality by identity, not by field values."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by identity so entities work correctly in sets and dicts."""
        return hash(self.id)

    def _assign_together(self, **changes: object) -> None:
        """Change related fields in one step.

        A cross-field validator re-runs on every single assignment, so two
        fields that are valid only together cannot be assigned one after the
        other. This builds a validated copy with changes (every
        validator runs, untouched fields keep their values) and only then
        takes it over; if validation fails, nothing changes. Private
        attributes such as pending events are kept.
        """
        candidate = validated_copy(self, **changes)
        self.__dict__.update(candidate.__dict__)
        self.__pydantic_fields_set__ |= candidate.__pydantic_fields_set__
