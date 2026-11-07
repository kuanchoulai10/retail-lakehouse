"""Define the Store abstract base class."""

from __future__ import annotations

from abc import ABC

from base._inheritance_guard import enforce_max_depth


class Store(ABC):
    """Infrastructure persistence that is not an aggregate repository.

    Use Store for persistence concerns that do not manage the lifecycle
    of a domain aggregate (e.g., event outbox, audit log storage).
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Enforce port + adapter inheritance depth (max 2)."""
        super().__init_subclass__(**kwargs)
        enforce_max_depth(cls, Store, 2)
