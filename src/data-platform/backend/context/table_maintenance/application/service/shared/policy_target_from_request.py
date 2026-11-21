"""Define the policy_target_from_request function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.outbound.table import (
    CatalogNotFoundError,
    TableMetadataRef,
)
from context.table_maintenance.application.service.shared.translate_domain_errors import translate_domain_errors

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
    table is NotFoundError. With ``must_exist`` a catalog or namespace must also exist; it may
    hold no table. A catalog the platform's credential cannot read raises
    CatalogAccessDeniedError, untouched.
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
            try:
                table = gateway.load_table(ref)
            except CatalogNotFoundError as exc:
                raise NotFoundError(str(exc)) from exc
            if table is None:
                raise NotFoundError(f"table {'.'.join(path)} not found")
            table_uuid = table.table_uuid
        with translate_domain_errors():
            return PolicyTarget(type=kind, path=path, table_uuid=table_uuid)
    if must_exist:
        try:
            exists = _exists(gateway, kind, path)
        except CatalogNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        if not exists:
            raise NotFoundError(f"{kind} {'.'.join(path)} not found")
    return target


def _exists(gateway: ReadTableMetadataGateway, kind: PolicyTargetType, path: tuple[str, ...]) -> bool:
    if kind == PolicyTargetType.CATALOG:
        return gateway.catalog_exists(path[0])
    return gateway.namespace_exists(path[0], ".".join(path[1:]))
