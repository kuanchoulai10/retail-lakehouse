"""Define the DiscoveryDecider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.service.shared import candidate_policy_targets
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    decide_table_discovery,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        DiscoveryDecision,
        TableDiscoveryPolicy,
        TableDiscoveryPolicyId,
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
    walk (``for_table``). Either way the decision is ``decide_table_discovery``'s, so the default
    decides a table nothing on its walk is attached to.
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

    def decide(self, name: TableName, table_uuid: str) -> DiscoveryDecision:
        """Decide the table by its current name and its uuid."""
        return decide_table_discovery(name, table_uuid, self._attachments, self._policies)
