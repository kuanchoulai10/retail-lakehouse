"""Define the Pydantic EntityId base class."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, RootModel

from base._inheritance_guard import enforce_max_depth


class EntityId(RootModel[str]):
    """A typed identifier for an Entity.

    Wraps a raw string in a distinct type so that ids of different Entity
    kinds cannot be mixed up: ``OrderId("1") != UserId("1")``. Built
    positionally, frozen, hashable and strict (only a ``str`` is accepted).

    Subclass per Entity type::

        class OrderId(EntityId):
            pass
    """

    model_config = ConfigDict(frozen=True, strict=True)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce flat hierarchy: concrete ids extend EntityId directly (max depth 1)."""
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, EntityId, 1)

    @property
    def value(self) -> str:
        """Return the raw identifier string."""
        return self.root

    def __str__(self) -> str:
        """Return the raw identifier string."""
        return self.root
