"""Define the Store abstract base class."""

from __future__ import annotations

from abc import ABC


class Store(ABC):
    """Infrastructure persistence that is not an aggregate repository.

    Use Store for persistence concerns that do not manage the lifecycle
    of a domain aggregate (e.g., event outbox, audit log storage).
    """
