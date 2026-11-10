"""Define the Pydantic Entity base class."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from base._inheritance_guard import enforce_max_depth
from base.entity_id import EntityId
from base.validated_copy import validated_copy


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

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        """Assign a field, leaving the entity unchanged when the assignment is rejected.

        Pydantic stores the value before a cross-field validator runs and does
        not take it back on failure, so the previous value and the set of
        explicitly assigned fields are restored here.
        """
        if name not in type(self).model_fields:
            super().__setattr__(name, value)
            return
        previous = self.__dict__[name]
        fields_set = set(self.__pydantic_fields_set__)
        try:
            super().__setattr__(name, value)
        except Exception:
            self.__dict__[name] = previous
            self.__pydantic_fields_set__.clear()
            self.__pydantic_fields_set__.update(fields_set)
            raise

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
