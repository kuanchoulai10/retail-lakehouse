"""Internal helper: rebuild a model from its field values with changes applied."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Mapping


def rebuild[M: BaseModel](model: M, changes: Mapping[str, object]) -> M:
    """Return a new ``model`` built from its field values plus ``changes``, running every validator.

    An unknown field name raises ``TypeError`` naming the class. Private
    attributes (an aggregate's pending events) are not carried over.
    """
    fields = type(model).model_fields
    unknown = sorted(changes.keys() - fields.keys())
    if unknown:
        raise TypeError(f"{type(model).__name__} has no field {', '.join(unknown)}")
    data = {name: getattr(model, name) for name in fields} | dict(changes)
    return type(model).model_validate(data, by_alias=False, by_name=True)
