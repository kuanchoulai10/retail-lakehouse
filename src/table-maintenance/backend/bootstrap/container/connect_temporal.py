"""Provide the connect_temporal function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.client import Client

if TYPE_CHECKING:
    from bootstrap.configs import TemporalSettings


async def connect_temporal(settings: TemporalSettings) -> Client:
    """Connect a Temporal client on the running event loop."""
    return await Client.connect(settings.address, namespace=settings.namespace)
