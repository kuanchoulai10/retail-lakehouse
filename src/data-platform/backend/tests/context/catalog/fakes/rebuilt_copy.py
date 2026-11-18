"""Define the rebuilt_copy helper."""

from __future__ import annotations

from pydantic import BaseModel


def rebuilt_copy[M: BaseModel](model: M, **changes: object) -> M:
    """Return a validated copy of an aggregate; it shares no mutable state and holds no pending events.

    The copy is built from the field values as they are (not ``model_dump``, which masks secrets).
    """
    data = {name: getattr(model, name) for name in type(model).model_fields} | changes
    return type(model).model_validate(data, by_alias=False, by_name=True)
