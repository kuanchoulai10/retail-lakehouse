"""Define the Gateway abstract base class."""

from __future__ import annotations

from abc import ABC


class Gateway(ABC):
    """Port for interacting with external systems.

    Use Gateway for operations that cross a system boundary: reading from
    external catalogs, submitting jobs to orchestrators, sending notifications,
    publishing events to message brokers, etc.
    """
