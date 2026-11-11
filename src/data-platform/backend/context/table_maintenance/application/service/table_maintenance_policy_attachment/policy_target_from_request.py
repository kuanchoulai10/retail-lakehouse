"""Define the policy_target_from_request function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.outbound.table import (
    ReadTableMetadataGatewayListInput,
    TableMetadataRef,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway


def policy_target_from_request(
    gateway: ReadTableMetadataGateway,
    target_type: str,
    path: tuple[str, ...],
    table_uuid: str | None = None,
    *,
    must_exist: bool,
) -> PolicyTarget:
    """Build the target a request names.

    A table target takes its uuid from the catalog unless ``table_uuid`` is given, and a missing
    table is NotFoundError. With ``must_exist`` a catalog or namespace must also hold at least one
    table, because the table-reading gateway cannot list catalogs or namespaces and an empty
    namespace reads as a missing one.
    """
    with translate_domain_errors():
        kind = PolicyTargetType(target_type)
        if kind == PolicyTargetType.TABLE and len(path) < 3:  # noqa: PLR2004
            raise ValueError("a table target path is catalog, namespace levels and table name")
        if kind != PolicyTargetType.TABLE:
            target = PolicyTarget(type=kind, path=path)
    if kind == PolicyTargetType.TABLE:
        ref = TableMetadataRef(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1])
        if table_uuid is None:
            table = gateway.load_table(ref)
            if table is None:
                raise NotFoundError(f"table {'.'.join(path)} not found")
            table_uuid = table.table_uuid
        with translate_domain_errors():
            return PolicyTarget(type=kind, path=path, table_uuid=table_uuid)
    if must_exist:
        namespace = ".".join(path[1:]) or None
        if not gateway.list_tables(ReadTableMetadataGatewayListInput(catalog=path[0], namespace=namespace)):
            raise NotFoundError(f"{kind} {'.'.join(path)} not found")
    return target
