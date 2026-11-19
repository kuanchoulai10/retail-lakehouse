"""Define the TableMaintenancePoliciesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base import Repository
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicy,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from base import EntityId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        TableMaintenancePolicyName,
        TableMaintenancePolicyVersion,
    )


class TableMaintenancePoliciesRepo(Repository[TableMaintenancePolicy]):
    """Persist and query TableMaintenancePolicy aggregates and their versions.

    A policy is stored and found by its ``mp-`` id; names are unique, so ``create`` of a
    second policy with a taken name raises ConflictError, whatever its id.
    """

    @abstractmethod
    def get_by_name(self, name: TableMaintenancePolicyName) -> TableMaintenancePolicy | None:
        """Return the policy with the given name at its current version, or None."""

    @abstractmethod
    def get_many(self, ids: Sequence[EntityId]) -> list[TableMaintenancePolicy]:
        """Return the policies that exist among ``ids``, in no particular order."""

    @abstractmethod
    def update(self, policy: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Persist the replaced policy and write its new version row in the same transaction."""

    @abstractmethod
    def get_version(self, policy_id: EntityId, version: int) -> TableMaintenancePolicyVersion | None:
        """Return one version of a policy, or None."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the policy and all its versions; raise ConflictError when it is attached anywhere."""
