"""Define the request_discovery_scan function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PolicyTargetType
from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import PolicyTarget
    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway

logger = logging.getLogger(__name__)


def request_discovery_scan(
    discovery_requests: SendDiscoveryRequestGateway, target: PolicyTarget, *, change_id: str
) -> bool:
    """Request a scan of the smallest scope covering a place whose discovery policy changed; return whether sent.

    The scope is the whole catalog for a catalog, the namespace for a namespace, and the table's
    namespace for a table. The request runs under
    ``change_id``, so it never joins a scan that read the policies before the change. It is best
    effort: a request that cannot be sent is logged and the change it follows stands.
    """
    scope_catalog = target.path[0]
    if target.type == PolicyTargetType.CATALOG:
        namespace = None
    elif target.type == PolicyTargetType.NAMESPACE:
        namespace = ".".join(target.path[1:])
    else:
        namespace = ".".join(target.path[1:-1])
    try:
        discovery_requests.send(SendDiscoveryRequestGatewayInput(scope_catalog, namespace, change_id=change_id))
    except Exception:
        scope = f"catalog {scope_catalog}" if namespace is None else f"namespace {namespace} of catalog {scope_catalog}"
        logger.exception("could not request a discovery of %s after discovery policy change %s", scope, change_id)
        return False
    return True
