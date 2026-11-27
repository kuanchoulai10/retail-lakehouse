"""Define the decide_table_discovery domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import ManagementDecision

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicy
    from context.table_maintenance.application.domain.service.shared import NearestPolicy


def decide_table_discovery(
    name: TableName,
    nearest: NearestPolicy[TableDiscoveryPolicyId] | None,
    policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy],
) -> ManagementDecision:
    """Decide a table by its nearest discovery policy (``nearest_discovery_policy``, docs/adr/0012).

    With no policy on the table's walk nothing decides, which manages nothing
    (``ManagementDecision.nothing_attached``); so does a nearest policy missing from ``policies``,
    which only a race with that policy's delete can cause.
    """
    if nearest is None or nearest.policy_id not in policies:
        return ManagementDecision.nothing_attached()
    return policies[nearest.policy_id].should_manage(name)
