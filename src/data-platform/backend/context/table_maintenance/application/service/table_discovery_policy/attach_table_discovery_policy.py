"""Define the AttachTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import CatalogId, NamespaceId, PolicyTargetType, TableId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    AttachTableDiscoveryPolicyUseCase,
    AttachTableDiscoveryPolicyUseCaseInput,
    AttachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import policy_target_from_request, translate_domain_errors
from context.table_maintenance.application.service.table_discovery_policy.request_discovery_scan import (
    request_discovery_scan,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.shared import PolicyTarget, TableDiscoveryPolicyId
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendDiscoveryRequestGateway,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class AttachTableDiscoveryPolicyService(AttachTableDiscoveryPolicyUseCase):
    """Attach a discovery policy to a catalog, namespace or table, replacing the one it holds."""

    def __init__(  # noqa: PLR0913
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        tables_repo: TablesRepo,
        gateway: ReadTableMetadataGateway,
        discovery_requests: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the policy and place repos, the catalog gateway, the discovery requests, the clock and change ids."""
        self._policies_repo = policies_repo
        self._catalogs_repo = catalogs_repo
        self._namespaces_repo = namespaces_repo
        self._tables_repo = tables_repo
        self._gateway = gateway
        self._discovery_requests = discovery_requests
        self._clock = clock
        self._new_change_id = new_change_id

    def execute(self, request: AttachTableDiscoveryPolicyUseCaseInput) -> AttachTableDiscoveryPolicyUseCaseOutput:
        """Attach the policy; a place or policy that does not exist is NotFoundError.

        The place must exist in the catalog, though a catalog or namespace may be empty, and a table is
        found by the uuid the catalog gives it. A place in a catalog the platform's credential cannot
        read raises CatalogAccessDeniedError. A catalog or namespace seen for the first time is
        registered; a table discovery has not seen yet is registered undecided, so the scan this
        requests decides it. A save from a copy someone else saved over since raises
        ConcurrentUpdateError and requests nothing. Once saved, the smallest scope covering the place
        is scanned (its catalog for a catalog, its namespace otherwise) under a new change id, best
        effort: a request that cannot be sent is logged, and the attach stands.
        """
        with translate_domain_errors():
            policy_name = TableDiscoveryPolicyName(value=request.policy_name)
        target = policy_target_from_request(self._gateway, request.target_type, request.path)
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.policy_name} not found")
        with translate_domain_errors():
            self._save(target, policy.id, self._clock())
        self._request_scan(target)
        return AttachTableDiscoveryPolicyUseCaseOutput(
            target_type=target.type.value,
            path=target.path,
            table_uuid=target.table_uuid,
            policy_id=policy.id.value,
            policy_name=policy.name.value,
        )

    def _save(self, target: PolicyTarget, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        if target.type == PolicyTargetType.CATALOG:
            self._save_catalog(CatalogId(target.path[0]), policy_id, now)
        elif target.type == PolicyTargetType.NAMESPACE:
            self._save_namespace(NamespaceId.of(target.path[0], target.path[1:]), policy_id, now)
        else:
            self._save_table(target, policy_id, now)

    def _save_catalog(self, catalog_id: CatalogId, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        catalog = self._catalogs_repo.get(catalog_id)
        if catalog is None:
            catalog = Catalog.register(catalog_id, now)
            catalog.attach_discovery_policy(policy_id, now)
            self._catalogs_repo.create(catalog)
            return
        catalog.attach_discovery_policy(policy_id, now)
        self._catalogs_repo.update(catalog)

    def _save_namespace(self, namespace_id: NamespaceId, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        namespace = self._namespaces_repo.get(namespace_id)
        if namespace is None:
            namespace = Namespace.register(namespace_id, now)
            namespace.attach_discovery_policy(policy_id, now)
            self._namespaces_repo.create(namespace)
            return
        namespace.attach_discovery_policy(policy_id, now)
        self._namespaces_repo.update(namespace)

    def _save_table(self, target: PolicyTarget, policy_id: TableDiscoveryPolicyId, now: datetime) -> None:
        table_id = TableId(target.table_uuid or "")
        table = self._tables_repo.get(table_id)
        if table is None:
            path = target.path
            name = TableName(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1])
            table = Table.register_undecided(table_id, name, now)
            table.attach_discovery_policy(policy_id, now)
            self._tables_repo.create(table)
            return
        table.attach_discovery_policy(policy_id, now)
        self._tables_repo.update(table)

    def _request_scan(self, target: PolicyTarget) -> None:
        request_discovery_scan(self._discovery_requests, target, change_id=self._new_change_id())
