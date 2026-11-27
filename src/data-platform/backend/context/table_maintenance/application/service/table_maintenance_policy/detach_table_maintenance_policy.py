"""Define the DetachTableMaintenancePolicyService."""

from __future__ import annotations

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
from context.table_maintenance.application.domain.model.table_maintenance_policy import TableMaintenancePolicyName
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    DetachTableMaintenancePolicyUseCase,
    DetachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_policy.notify_policy_change import (
    notify_policy_change,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.shared import TableMaintenancePolicyId
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import SendTableChangeGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class DetachTableMaintenancePolicyService(DetachTableMaintenancePolicyUseCase):
    """Detach a maintenance policy from the catalog, namespace or table at a path."""

    def __init__(  # noqa: PLR0913
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        tables_repo: TablesRepo,
        table_changes: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the policy and place repos, the table change gateway and the clock."""
        self._policies_repo = policies_repo
        self._catalogs_repo = catalogs_repo
        self._namespaces_repo = namespaces_repo
        self._tables_repo = tables_repo
        self._table_changes = table_changes
        self._clock = clock

    def execute(self, request: DetachTableMaintenancePolicyUseCaseInput) -> DetachTableMaintenancePolicyUseCaseOutput:
        """Detach the policy; an unknown policy, a place with no record or one not holding it is NotFoundError.

        A bad target type, or a path that names no place of its type, is ValidationError. The catalog is
        not read: a table is found by the name table maintenance knows it by, so a place whose catalog
        or namespace is gone (orphaned) is detached the same way. The place keeps its record. A save from
        a copy someone else saved over since raises ConcurrentUpdateError. Every managed table whose
        applicable policy changed is told so; a refused detach tells none.
        """
        with translate_domain_errors():
            policy_name = TableMaintenancePolicyName(value=request.policy_name)
            kind = PolicyTargetType(request.target_type)
            place = None if kind == PolicyTargetType.TABLE else PolicyTarget(type=kind, path=request.path)
            if place is None and len(request.path) < 3:  # noqa: PLR2004
                raise ValueError("a table target path is catalog, namespace levels and table name")
        policy = self._policies_repo.get_by_name(policy_name)
        if policy is None:
            raise NotFoundError(f"table maintenance policy {request.policy_name} not found")
        policy_id = policy.id
        path = request.path

        def change() -> None:
            if place is None:
                self._detach_table(path, policy_id)
            else:
                self._detach_place(place, policy_id)

        notify_policy_change(
            self._tables_repo,
            self._policies_repo,
            self._catalogs_repo,
            self._namespaces_repo,
            self._table_changes,
            change,
        )
        return DetachTableMaintenancePolicyUseCaseOutput()

    def _detach_place(self, target: PolicyTarget, policy_id: TableMaintenancePolicyId) -> None:
        now = self._clock()
        described = f"{target.type} {'.'.join(target.path)}"
        if target.type == PolicyTargetType.CATALOG:
            catalog = self._catalogs_repo.get(CatalogId(target.path[0]))
            if catalog is None:
                raise NotFoundError(f"{described} not found")
            _detach(lambda: catalog.detach_maintenance_policy(policy_id, now))
            with translate_domain_errors():
                self._catalogs_repo.update(catalog)
            return
        namespace = self._namespaces_repo.get(NamespaceId.of(target.path[0], target.path[1:]))
        if namespace is None:
            raise NotFoundError(f"{described} not found")
        _detach(lambda: namespace.detach_maintenance_policy(policy_id, now))
        with translate_domain_errors():
            self._namespaces_repo.update(namespace)

    def _detach_table(self, path: tuple[str, ...], policy_id: TableMaintenancePolicyId) -> None:
        """Detach from the live row of the name holding the policy, else from the latest updated one.

        A table recreated in the catalog under the same name has two live rows until a scan drops the
        old one; the policy may sit on either.
        """
        with translate_domain_errors():
            name = TableName(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1])
        rows = self._tables_repo.list_by_name(name)
        if not rows:
            raise NotFoundError(f"table {'.'.join(path)} not found")
        table = next((row for row in rows if row.maintenance_policy_id == policy_id), rows[0])
        _detach(lambda: table.detach_maintenance_policy(policy_id, self._clock()))
        with translate_domain_errors():
            self._tables_repo.update(table)


def _detach(detach: Callable[[], None]) -> None:
    try:
        detach()
    except PolicyNotAttached as exc:
        raise NotFoundError(str(exc)) from exc
