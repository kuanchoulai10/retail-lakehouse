"""Provide the setting_paths function."""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Union, get_args, get_origin

from pydantic import BaseModel, SecretStr

if TYPE_CHECKING:
    from collections.abc import Iterator


def setting_paths(model: type[BaseModel], prefix: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], bool]]:
    """Yield the path of every field of ``model`` at any depth, and whether that field holds a secret."""
    for name, field in model.model_fields.items():
        path = (*prefix, name)
        kinds = _kinds(field.annotation)
        yield path, SecretStr in kinds
        for kind in kinds:
            if isinstance(kind, type) and issubclass(kind, BaseModel):
                yield from setting_paths(kind, path)


def _kinds(annotation: object) -> tuple[object, ...]:
    if get_origin(annotation) in (Union, types.UnionType):
        return tuple(arg for arg in get_args(annotation) if arg is not type(None))
    return (annotation,)
