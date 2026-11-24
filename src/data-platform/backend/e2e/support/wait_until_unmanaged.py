"""Provide wait_until_unmanaged, which waits until the platform no longer maintains a table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from e2e.support.reconciliation_running import reconciliation_running
from e2e.support.wait_until import wait_until

if TYPE_CHECKING:
    from temporalio.client import Client

    from e2e.support.platform_api import PlatformApi
    from e2e.support.temporal_session import TemporalSession

UNMANAGE_TIMEOUT_SECONDS = 600


def wait_until_unmanaged(platform: PlatformApi, temporal: TemporalSession[Client], place: tuple[str, str, str]) -> None:
    """Wait until the table at ``(catalog, namespace, table)`` is not managed and its reconciliation stopped."""

    def settled() -> bool:
        found = platform.table(*place)
        if found is None:
            return True
        if found["status"] == "managed" or reconciliation_running(temporal, found["uuid"]):
            raise AssertionError(f"{found['status']}, reconciliation of {found['uuid']} may still run")
        return True

    wait_until(settled, timeout=UNMANAGE_TIMEOUT_SECONDS, interval=10, what=f"{'.'.join(place)} unmanaged")
