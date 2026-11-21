"""Define the decide_table_discovery domain service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicy
from context.table_maintenance.application.domain.service.shared import candidate_policy_targets, nearest_attached

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        DiscoveryDecision,
        TableDiscoveryPolicyId,
    )
    from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachment,
    )

# The default's timestamps never reach a decision; only its fixed id, version and content do.
_DEFAULT_CREATED_AT = datetime(1970, 1, 1, tzinfo=UTC)


def decide_table_discovery(
    name: TableName,
    table_uuid: str,
    attachments: Iterable[TableDiscoveryPolicyAttachment],
    policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy],
) -> DiscoveryDecision:
    """Decide a table by the policy of its nearest attachment (docs/adr/0012).

    The walk runs from the table itself (by its uuid) through its namespaces, deepest first, to its
    catalog, and the first attachment replaces its parents whole. An attachment whose policy is not
    in ``policies`` is skipped, which only a race with that policy's delete can cause. With no
    attachment on the walk, the platform default decides with its fixed content at version 1.
    It relies on target keys being unique among ``attachments`` (one attachment per target, as the
    repo guarantees); with two on one key, the later one would win.
    """
    attached = {
        attachment.target.key(): policies[attachment.policy_id]
        for attachment in attachments
        if attachment.policy_id in policies
    }
    nearest = nearest_attached(candidate_policy_targets(name, table_uuid), attached)
    policy = TableDiscoveryPolicy.create_default(_DEFAULT_CREATED_AT) if nearest is None else nearest[1]
    return policy.decide(name)
