"""Define the PolicyTarget value object."""

from __future__ import annotations

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.policy_target_type import (
    PolicyTargetType,
)


class PolicyTarget(ValueObject):
    """Where a policy is attached: a catalog, a namespace or a table.

    ``path`` is the catalog name followed by the namespace levels, followed by
    the table name for a table. A table is also identified by its uuid, so a
    renamed or moved table keeps the policy it holds.
    """

    type: PolicyTargetType
    path: tuple[str, ...]
    table_uuid: str | None = None

    @model_validator(mode="after")
    def _shape_matches_type(self) -> PolicyTarget:
        is_table = self.type == PolicyTargetType.TABLE
        if is_table and self.table_uuid is None:
            raise ValueError("a table target requires table_uuid")
        if not is_table and self.table_uuid is not None:
            raise ValueError("table_uuid is only for a table target")
        if self.type == PolicyTargetType.CATALOG and len(self.path) != 1:
            raise ValueError("a catalog target path has exactly one element")
        if self.type != PolicyTargetType.CATALOG and len(self.path) < 2:  # noqa: PLR2004
            raise ValueError(f"a {self.type} target path has at least two elements")
        if any(not part or "\x1f" in part for part in self.path):
            raise ValueError("path elements must be non-empty")
        return self

    def key(self) -> str:
        """Return the key that names this target: one place, whatever path it is read under.

        A table is keyed by its uuid (``table:<uuid>``), so a renamed or moved table is the same
        place; a catalog or namespace by its type and unit-separated path.
        """
        if self.type == PolicyTargetType.TABLE:
            return f"table:{self.table_uuid}"
        return f"{self.type}:" + "\x1f".join(self.path)
