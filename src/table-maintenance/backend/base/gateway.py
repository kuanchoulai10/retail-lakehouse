"""Define the Gateway abstract base class."""

from __future__ import annotations

from abc import ABC

from base._inheritance_guard import enforce_max_depth


class Gateway(ABC):
    """Port for interacting with external systems.

    Use Gateway for operations that cross a system boundary: reading from
    external catalogs, submitting jobs to orchestrators, sending notifications,
    publishing events to message brokers, etc.
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Enforce port + adapter inheritance depth (max 2)."""
        super().__init_subclass__(**kwargs)
        enforce_max_depth(cls, Gateway, 2)
