"""Define validated_copy."""

from __future__ import annotations

from pydantic import BaseModel


def validated_copy[M: BaseModel](model: M, /, **changes: object) -> M:
    """Return a copy of ``model`` with ``changes`` applied, running every validator.

    Pydantic's ``model_copy(update=...)`` skips validation; this rebuilds
    the model from its field values so field and model validators see the
    changed object. An unknown field name raises ``TypeError``. Private
    attributes (an aggregate's pending events) are not carried over.
    """
    fields = type(model).model_fields
    unknown = sorted(changes.keys() - fields.keys())
    if unknown:
        raise TypeError(f"{type(model).__name__} has no field {', '.join(unknown)}")
    data = {name: getattr(model, name) for name in fields} | changes
    return type(model).model_validate(data, by_alias=False, by_name=True)
