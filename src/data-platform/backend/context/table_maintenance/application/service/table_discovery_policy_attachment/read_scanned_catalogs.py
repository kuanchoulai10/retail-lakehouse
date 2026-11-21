"""Define read_scanned_catalogs, the scanned catalogs as the repos hold them now."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    scanned_catalogs,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


def read_scanned_catalogs(
    policies_repo: TableDiscoveryPoliciesRepo, attachments_repo: TableDiscoveryPolicyAttachmentsRepo
) -> tuple[str, ...]:
    """Return the catalogs discovery scans, sorted: those a policy that can manage is attached in."""
    attachments = attachments_repo.list_all()
    policies = {p.id: p for p in policies_repo.get_many(list({a.policy_id for a in attachments}))}
    return scanned_catalogs(attachments, policies)
