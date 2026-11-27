"""Define the DiscoveryDecider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.shared import candidate_policy_targets
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    decide_table_discovery,
    scanned_catalogs,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        ManagementDecision,
        TableDiscoveryPolicy,
    )
    from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachment,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )


class DiscoveryDecider:
    """Decide discovered tables by their nearest discovery policy, from attachments read once.

    A scan reads its catalog's attachments and their policies once (``for_catalog``) and decides
    every table it lists from them; a catalog event reads only the attachments on its one table's
    walk (``for_table``). Either way the decision is ``decide_table_discovery``'s, so a table
    nothing on its walk is attached to is not managed, and nothing decided it.
    """

    def __init__(
        self,
        attachments: Sequence[TableDiscoveryPolicyAttachment],
        policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy],
    ) -> None:
        """Hold the attachments read and the policies they point at."""
        self._attachments = tuple(attachments)
        self._policies = dict(policies)

    @classmethod
    def for_catalog(
        cls,
        catalog: str,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        policies_repo: TableDiscoveryPoliciesRepo,
    ) -> DiscoveryDecider:
        """Read the attachments in ``catalog`` and their policies, to decide any table in it."""
        return cls._reading(attachments_repo.list_in_catalog(catalog), policies_repo)

    @classmethod
    def for_table(
        cls,
        name: TableName,
        table_uuid: str,
        attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        policies_repo: TableDiscoveryPoliciesRepo,
    ) -> DiscoveryDecider:
        """Read the attachments on one table's walk and their policies, to decide that table."""
        targets = candidate_policy_targets(name, table_uuid)
        return cls._reading(attachments_repo.get_many_by_targets(targets), policies_repo)

    @classmethod
    def _reading(
        cls,
        attachments: Sequence[TableDiscoveryPolicyAttachment],
        policies_repo: TableDiscoveryPoliciesRepo,
    ) -> DiscoveryDecider:
        policy_ids = list(dict.fromkeys(attachment.policy_id for attachment in attachments))
        policies = policies_repo.get_many(policy_ids)
        return cls(attachments, {policy.id: policy for policy in policies})

    def decide(self, name: TableName, table_uuid: str) -> ManagementDecision:
        """Decide the table by its current name and its uuid."""
        return decide_table_discovery(name, table_uuid, self._attachments, self._policies)

    def has_any_policy(self) -> bool:
        """Return whether an attachment read points at a stored policy.

        Read ``for_catalog``, this says whether the catalog is scanned. When it is not, nothing is
        attached in the catalog and every table there is not managed, so a scan needs no catalog read
        to decide them.
        """
        return bool(scanned_catalogs(self._attachments, self._policies))
