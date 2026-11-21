"""Define the scanned_catalogs domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        TableDiscoveryPolicy,
        TableDiscoveryPolicyId,
    )
    from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachment,
    )


def scanned_catalogs(
    attachments: Iterable[TableDiscoveryPolicyAttachment],
    policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy],
) -> tuple[str, ...]:
    """Return the catalogs discovery scans, sorted and each once.

    A catalog is scanned when an attachment in it (on the catalog, a namespace or a table) points at a
    policy that could resolve some table to ``manage``. An attachment whose policy is not in
    ``policies`` is skipped, as ``decide_table_discovery`` skips it.
    """
    return tuple(
        sorted(
            {
                attachment.catalog
                for attachment in attachments
                if (policy := policies.get(attachment.policy_id)) is not None and policy.can_manage()
            }
        )
    )
