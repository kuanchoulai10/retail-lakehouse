"""Define the TableMaintenancePoliciesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicy,
)

if TYPE_CHECKING:
    from base import EntityId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicyName,
        TableMaintenancePolicyVersion,
    )


class TableMaintenancePoliciesRepo(Repository[TableMaintenancePolicy]):
    """Persist and query TableMaintenancePolicy aggregates and their versions."""

    @abstractmethod
    def update(self, policy: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Persist the replaced policy and write its new version row in the same transaction."""

    @abstractmethod
    def get_version(self, name: TableMaintenancePolicyName, version: int) -> TableMaintenancePolicyVersion | None:
        """Return one version of a policy, or None."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the policy and all its versions; raise ConflictError when it is attached anywhere."""
