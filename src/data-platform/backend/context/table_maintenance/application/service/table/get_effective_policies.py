"""Define the GetEffectivePoliciesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_ID
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import (
    GetEffectivePoliciesUseCase,
    GetEffectivePoliciesUseCaseInput,
    GetEffectivePoliciesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import CatalogNotFoundError
from context.table_maintenance.application.service.shared import PolicyHolders, policy_target_fields

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class GetEffectivePoliciesService(GetEffectivePoliciesUseCase):
    """Answer, for each kind of policy, which one applies to a place and from which level.

    The place's holders (its table, the namespaces enclosing it and its catalog) are read once, as
    ``PolicyHolders.of_place`` reads them, and each kind takes its own nearest holder: a table holding a
    policy of one kind leaves the other kind at its own level. With nothing attached the maintenance
    platform default applies, read from its repo, and no discovery policy applies (every discovery
    field is None). By location a catalog, namespace or table the catalog does not hold is
    NotFoundError, and a catalog the platform cannot read raises CatalogAccessDeniedError, as attaching
    there does; by uuid a table table maintenance has no record of is NotFoundError. A place is named by
    uuid or by location, never both (ValidationError).
    """

    def __init__(  # noqa: PLR0913
        self,
        maintenance_policies_repo: TableMaintenancePoliciesRepo,
        discovery_policies_repo: TableDiscoveryPoliciesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
    ) -> None:
        """Bind both kinds' policies, the places, the catalog gateway and the tables."""
        self._maintenance_policies_repo = maintenance_policies_repo
        self._discovery_policies_repo = discovery_policies_repo
        self._catalogs_repo = catalogs_repo
        self._namespaces_repo = namespaces_repo
        self._gateway = gateway
        self._tables_repo = tables_repo

    def execute(self, request: GetEffectivePoliciesUseCaseInput) -> GetEffectivePoliciesUseCaseOutput:
        """Return the maintenance and the discovery entry of the place the request names."""
        if request.table_uuid is not None and request.catalog is not None:
            raise ValidationError("name a place by uuid or by location, not both")
        holders = PolicyHolders.of_place(
            self._gateway,
            self._tables_repo,
            self._catalogs_repo,
            self._namespaces_repo,
            catalog=request.catalog,
            namespace=request.namespace,
            table=request.table,
            table_uuid=request.table_uuid,
        )
        if request.catalog is not None and request.table is None:
            self._require_place(request.catalog, request.namespace)
        return GetEffectivePoliciesUseCaseOutput(
            maintenance=self._maintenance_entry(holders),
            discovery=self._discovery_entry(holders),
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

    def _maintenance_entry(self, holders: PolicyHolders) -> GetEffectivePoliciesUseCaseOutput.MaintenanceEntry:
        """Answer the maintenance policy ``nearest_maintenance_policy`` finds, else the platform default."""
        nearest = holders.nearest_maintenance_policy()
        policy_id = DEFAULT_POLICY_ID if nearest is None else nearest.policy_id
        policy = self._maintenance_policies_repo.get(policy_id)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {policy_id.value} not found")
        return GetEffectivePoliciesUseCaseOutput.MaintenanceEntry(
            policy_id=policy.id.value,
            policy_name=policy.name.value,
            version=policy.version,
            description=policy.content.description,
            dry_run=policy.content.dry_run,
            target=None if nearest is None else policy_target_fields(nearest.target),
        )

    def _discovery_entry(self, holders: PolicyHolders) -> GetEffectivePoliciesUseCaseOutput.DiscoveryEntry:
        """Answer the discovery policy ``nearest_discovery_policy`` finds for the place, as discovery decides it."""
        nearest = holders.nearest_discovery_policy()
        if nearest is None:
            return GetEffectivePoliciesUseCaseOutput.DiscoveryEntry(
                policy_id=None, policy_name=None, version=None, description=None, target=None
            )
        policy = self._discovery_policies_repo.get(nearest.policy_id)
        if policy is None:
            raise NotFoundError(f"table discovery policy {nearest.policy_id.value} not found")
        return GetEffectivePoliciesUseCaseOutput.DiscoveryEntry(
            policy_id=policy.id.value,
            policy_name=policy.name.value,
            version=policy.version,
            description=policy.description,
            target=policy_target_fields(nearest.target),
        )
