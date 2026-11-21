"""Define the GetEffectivePoliciesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import DEFAULT_DISCOVERY_POLICY_ID
from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_ID
from context.table_maintenance.application.domain.service.shared import nearest_attached
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import (
    GetEffectivePoliciesUseCase,
    GetEffectivePoliciesUseCaseInput,
    GetEffectivePoliciesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import CatalogNotFoundError
from context.table_maintenance.application.service.shared import policy_candidates, policy_target_fields

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.shared import PolicyTarget
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachmentsRepo,
    )


class GetEffectivePoliciesService(GetEffectivePoliciesUseCase):
    """Answer, for each kind of policy, which one applies to a place, from which level and through which attachment.

    Every kind walks the same candidates (``policy_candidates``) and takes its own nearest attachment, so a
    table attachment of one kind leaves the other kind at its own level. With nothing attached a kind's
    platform default applies, read from its repo. By location a catalog, namespace or table the catalog does
    not hold is NotFoundError, and a catalog the platform cannot read raises CatalogAccessDeniedError, as
    attaching there does; by uuid a table table maintenance has no record of is NotFoundError. A place is
    named by uuid or by location, never both (ValidationError).
    """

    def __init__(  # noqa: PLR0913
        self,
        maintenance_policies_repo: TableMaintenancePoliciesRepo,
        maintenance_attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        discovery_policies_repo: TableDiscoveryPoliciesRepo,
        discovery_attachments_repo: TableDiscoveryPolicyAttachmentsRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
    ) -> None:
        """Bind both kinds' policy and attachment repos, the catalog gateway and the tables repo."""
        self._maintenance_policies_repo = maintenance_policies_repo
        self._maintenance_attachments_repo = maintenance_attachments_repo
        self._discovery_policies_repo = discovery_policies_repo
        self._discovery_attachments_repo = discovery_attachments_repo
        self._gateway = gateway
        self._tables_repo = tables_repo

    def execute(self, request: GetEffectivePoliciesUseCaseInput) -> GetEffectivePoliciesUseCaseOutput:
        """Return the maintenance and the discovery entry of the place the request names."""
        if request.table_uuid is not None and request.catalog is not None:
            raise ValidationError("name a place by uuid or by location, not both")
        candidates = policy_candidates(
            self._gateway,
            self._tables_repo,
            catalog=request.catalog,
            namespace=request.namespace,
            table=request.table,
            table_uuid=request.table_uuid,
        )
        if request.catalog is not None and request.table is None:
            self._require_place(request.catalog, request.namespace)
        return GetEffectivePoliciesUseCaseOutput(
            maintenance=self._maintenance_entry(candidates),
            discovery=self._discovery_entry(candidates),
        )

    def _require_place(self, catalog: str, namespace: str | None) -> None:
        """Raise NotFoundError unless the catalog, or the namespace when one is named, exists.

        A table named by location needs no check: loading it already proved its place. A namespace read
        also answers for its catalog, which raises CatalogNotFoundError when it is gone.
        """
        place = catalog if namespace is None else f"{catalog}.{namespace}"
        try:
            if namespace is None:
                exists = self._gateway.catalog_exists(catalog)
            else:
                exists = self._gateway.namespace_exists(catalog, namespace)
        except CatalogNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        if not exists:
            raise NotFoundError(f"{'catalog' if namespace is None else 'namespace'} {place} not found")

    def _maintenance_entry(
        self, candidates: Sequence[PolicyTarget]
    ) -> GetEffectivePoliciesUseCaseOutput.MaintenanceEntry:
        attached = {a.target.key(): a for a in self._maintenance_attachments_repo.get_many_by_targets(candidates)}
        nearest = nearest_attached(candidates, attached)
        policy_id = DEFAULT_POLICY_ID if nearest is None else nearest[1].policy_id
        policy = self._maintenance_policies_repo.get(policy_id)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {policy_id.value} not found")
        return GetEffectivePoliciesUseCaseOutput.MaintenanceEntry(
            policy_id=policy.id.value,
            policy_name=policy.name.value,
            version=policy.version,
            description=policy.content.description,
            dry_run=policy.content.dry_run,
            target=None if nearest is None else policy_target_fields(nearest[0]),
            attachment_id=None if nearest is None else nearest[1].id.value,
        )

    def _discovery_entry(self, candidates: Sequence[PolicyTarget]) -> GetEffectivePoliciesUseCaseOutput.DiscoveryEntry:
        attached = {a.target.key(): a for a in self._discovery_attachments_repo.get_many_by_targets(candidates)}
        nearest = nearest_attached(candidates, attached)
        policy_id = DEFAULT_DISCOVERY_POLICY_ID if nearest is None else nearest[1].policy_id
        policy = self._discovery_policies_repo.get(policy_id)
        if policy is None:
            raise NotFoundError(f"table discovery policy {policy_id.value} not found")
        return GetEffectivePoliciesUseCaseOutput.DiscoveryEntry(
            policy_id=policy.id.value,
            policy_name=policy.name.value,
            version=policy.version,
            description=policy.content.description,
            no_match_outcome=policy.content.no_match_outcome.value,
            target=None if nearest is None else policy_target_fields(nearest[0]),
            attachment_id=None if nearest is None else nearest[1].id.value,
        )
