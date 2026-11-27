"""Define the nearest_discovery_policy domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.shared.nearest_policy import NearestPolicy
from context.table_maintenance.application.domain.service.shared.policy_holders_nearest_first import (
    policy_holders_nearest_first,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.catalog import Catalog
    from context.table_maintenance.application.domain.model.namespace import Namespace
    from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
    from context.table_maintenance.application.domain.model.table import Table, TableName


def nearest_discovery_policy(
    table: Table | None,
    namespaces: Sequence[Namespace],
    catalog: Catalog | None,
    *,
    name: TableName | None = None,
) -> NearestPolicy[TableDiscoveryPolicyId] | None:
    """Return the discovery policy nearest to a place and where it is attached; None when none is (docs/adr/0012).

    The walk is ``policy_holders_nearest_first``'s: the table, its namespaces deepest first, its
    catalog. The first that holds a discovery policy replaces every one above it whole.
    """
    for target, holder in policy_holders_nearest_first(table, namespaces, catalog, name=name):
        if holder.discovery_policy_id is not None:
            return NearestPolicy(target=target, policy_id=holder.discovery_policy_id)
    return None
