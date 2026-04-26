"""Define the Entity base class."""

from __future__ import annotations

from abc import ABC

from base.entity_id import EntityId


class Entity[ID: EntityId](ABC):
    """An object with a distinct identity that persists through state changes.

    Two Entities are equal when they share the same ``id``, even if every
    other attribute differs. This makes identity — not current state — the
    basis for equality and hashing.

    Examples: User(id, name, email), Order(id, total, status),
    Product(id, sku, price).

    Rules:
        - Identity: each Entity has a unique ``id`` that never changes.
        - Equality by identity: two instances with the same ``id`` are equal.
        - Mutable: state may change over the Entity's lifecycle.

    Usage::

        @dataclass(frozen=True)
        class UserId(EntityId):
            pass

        @dataclass(eq=False)
        class User(Entity[UserId]):
            name: str
            email: str

    Subclasses must use @dataclass(eq=False) so the identity-based
    __eq__ and __hash__ defined here are not overridden by dataclass-
    generated versions.
    """

    id: ID  # noqa: A003

    def __eq__(self, other: object) -> bool:
        """Compare equality by identity, not by attribute values."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by identity so entities work correctly in sets and dicts."""
        return hash(self.id)
