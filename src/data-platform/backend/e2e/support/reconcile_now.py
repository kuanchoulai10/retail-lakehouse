"""Provide reconcile_now, which asks the platform to check a table now and returns the record that check made."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from e2e.support.wait_until import wait_until

if TYPE_CHECKING:
    from e2e.support.platform_api import PlatformApi


def reconcile_now(platform: PlatformApi, table_uuid: str, *, timeout: float = 180) -> dict[str, Any]:
    """Post a reconcile and return the first record after it woken by ``reconcile_now``.

    Records from before the post are left out by id, so an older reconcile-now record never
    answers; a check that started nothing still records, so the wait ends either way.
    """
    path = f"/v1/tables/{table_uuid}/reconciliations"
    known = {record["reconciliation_id"] for record in platform.get(path)}
    platform.call("POST", f"/v1/tables/{table_uuid}/reconcile")

    def recorded() -> dict[str, Any] | None:
        new = [
            record
            for record in platform.get(path)
            if record["reconciliation_id"] not in known and record["wake_reasons"].get("reconcile_now", 0) >= 1
        ]
        return new[0] if new else None

    return wait_until(recorded, timeout=timeout, interval=2, what=f"the reconcile-now record of {table_uuid}")
