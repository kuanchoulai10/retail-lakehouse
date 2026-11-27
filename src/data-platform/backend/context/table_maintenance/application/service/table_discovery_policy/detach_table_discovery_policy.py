"""Define the DetachTableDiscoveryPolicyService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    NamespaceId,
    PolicyNotAttached,
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyName
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    DetachTableDiscoveryPolicyUseCase,
    DetachTableDiscoveryPolicyUseCaseInput,
    DetachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_discovery_policy.request_discovery_scan import (
    request_discovery_scan,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )


class DetachTableDiscoveryPolicyService(DetachTableDiscoveryPolicyUseCase):
    """Detach a discovery policy from the catalog, namespace or table at a path."""

    def __init__(  # noqa: PLR0913
        self,
        policies_repo: TableDiscoveryPoliciesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        tables_repo: TablesRepo,
        discovery_requests: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        """Bind the policy and place repos, the discovery requests, the clock and the change id generator."""
        self._policies_repo = policies_repo
        self._catalogs_repo = catalogs_repo
        self._namespaces_repo = namespaces_repo
        self._tables_repo = tables_repo
        self._discovery_requests = discovery_requests
        self._clock = clock
        self._new_change_id = new_change_id

    def execute(self, request: DetachTableDiscoveryPolicyUseCaseInput) -> DetachTableDiscoveryPolicyUseCaseOutput:
        """Detach the policy; an unknown policy, a place with no record or one not holding it is NotFoundError.

        A bad target type, or a path that names no place of its type, is ValidationError. The catalog is
        not read: a table is found by the name table maintenance knows it by, so a place whose catalog
        or namespace is gone (orphaned) is detached the same way. The place keeps its record. A save from
        a copy someone else saved over since raises ConcurrentUpdateError. Once saved, the smallest scope
        that covered the place is scanned under a new change id, best effort.
        """
        with translate_domain_errors():
            policy_name = TableDiscoveryPolicyName(value=request.policy_name)
            kind = PolicyTargetType(request.target_type)
            place = None if kind == PolicyTargetType.TABLE else PolicyTarget(type=kind, path=request.path)
            if place is None and len(request.path) < 3:  # noqa: PLR2004
                raise ValueError("a table target path is catalog, namespace levels and table name")
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"discovery policy {request.policy_name} not found")
        if place is None:
            target = self._detach_table(request.path, policy.id)
        else:
            target = self._detach_place(place, policy.id)
        request_discovery_scan(self._discovery_requests, target, change_id=self._new_change_id())
        return DetachTableDiscoveryPolicyUseCaseOutput()

    def _detach_place(self, target: PolicyTarget, policy_id: TableDiscoveryPolicyId) -> PolicyTarget:
        now = self._clock()
        described = f"{target.type} {'.'.join(target.path)}"
        if target.type == PolicyTargetType.CATALOG:
            catalog = self._catalogs_repo.get(CatalogId(target.path[0]))
            if catalog is None:
                raise NotFoundError(f"{described} not found")
            _detach(lambda: catalog.detach_discovery_policy(policy_id, now))
            with translate_domain_errors():
                self._catalogs_repo.update(catalog)
            return target
        namespace = self._namespaces_repo.get(NamespaceId.of(target.path[0], target.path[1:]))
        if namespace is None:
            raise NotFoundError(f"{described} not found")
        _detach(lambda: namespace.detach_discovery_policy(policy_id, now))
        with translate_domain_errors():
            self._namespaces_repo.update(namespace)
        return target

    def _detach_table(self, path: tuple[str, ...], policy_id: TableDiscoveryPolicyId) -> PolicyTarget:
        """Detach from the live row of the name holding the policy, else from the latest updated one.

        A table recreated in the catalog under the same name has two live rows until a scan drops the
        old one; the attachment may sit on either.
        """
        with translate_domain_errors():
            name = TableName(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1])
        rows = self._tables_repo.list_by_name(name)
        if not rows:
            raise NotFoundError(f"table {'.'.join(path)} not found")
        table = next((row for row in rows if row.discovery_policy_id == policy_id), rows[0])
        _detach(lambda: table.detach_discovery_policy(policy_id, self._clock()))
        with translate_domain_errors():
            self._tables_repo.update(table)
        with translate_domain_errors():
            return PolicyTarget(type=PolicyTargetType.TABLE, path=path, table_uuid=table.id.value)


def _detach(detach: Callable[[], None]) -> None:
    try:
        detach()
    except PolicyNotAttached as exc:
        raise NotFoundError(str(exc)) from exc
