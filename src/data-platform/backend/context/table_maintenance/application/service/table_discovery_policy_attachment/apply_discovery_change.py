"""Define apply_discovery_change, which runs a discovery policy change and then rescans what it affects."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    SyncDiscoverySchedulesGatewayInput,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment.read_scanned_catalogs import (
    read_scanned_catalogs,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        SyncDiscoverySchedulesGateway,
        TableDiscoveryPolicyAttachmentsRepo,
    )

logger = logging.getLogger(__name__)


def apply_discovery_change[T](  # noqa: PLR0913
    policies_repo: TableDiscoveryPoliciesRepo,
    attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
    discovery_requests: SendDiscoveryRequestGateway,
    schedules: SyncDiscoverySchedulesGateway,
    change: Callable[[], T],
    *,
    affected_catalogs: Callable[[], Collection[str]],
    change_id: str,
) -> T:
    """Run ``change``, then rescan the affected catalogs and sync the schedules; return what it returned.

    ``change`` raising propagates, and nothing else runs. Afterwards every affected catalog that is
    scanned before or after the change gets one catalog-wide scan under ``change_id``. A catalog that
    stopped being scanned is unmanaged by that final scan. The schedules are then synced: each catalog
    scanned after the change keeps or gets its schedule, and a catalog that stopped being scanned loses
    its schedule only once its final scan has started (otherwise its schedule's next firing does the
    same, and the worker start retires it). No other schedule is deleted, so a stale view of another
    change's catalogs cannot drop their schedules.

    Everything after the change is best effort: reading back the scanned catalogs or the affected ones,
    a scan or a sync that fails is logged and never fails the change.
    """
    before = read_scanned_catalogs(policies_repo, attachments_repo)
    result = change()
    try:
        after = read_scanned_catalogs(policies_repo, attachments_repo)
        affected = set(affected_catalogs())
    except Exception:
        logger.exception(
            "could not work out what discovery policy change %s affects; nothing rescanned or synced", change_id
        )
        return result
    started = _rescan(discovery_requests, sorted(affected & (set(before) | set(after))), change_id=change_id)
    left = sorted(set(before) - set(after))
    for catalog in left:
        if catalog in affected and catalog not in started:
            logger.warning(
                "keeping the discovery schedule of catalog %s, which is no longer scanned, until its final scan starts",
                catalog,
            )
    try:
        schedules.sync(
            SyncDiscoverySchedulesGatewayInput(catalogs=after, removed=tuple(c for c in left if c in started))
        )
    except Exception:
        logger.exception("could not sync the discovery schedules after discovery policy change %s", change_id)
    return result


def _rescan(discovery_requests: SendDiscoveryRequestGateway, catalogs: list[str], *, change_id: str) -> set[str]:
    started: set[str] = set()
    for catalog in catalogs:
        try:
            discovery_requests.send(SendDiscoveryRequestGatewayInput(catalog, None, change_id=change_id))
        except Exception:
            logger.exception(
                "could not start discovery in catalog %s after discovery policy change %s", catalog, change_id
            )
        else:
            started.add(catalog)
    return started
