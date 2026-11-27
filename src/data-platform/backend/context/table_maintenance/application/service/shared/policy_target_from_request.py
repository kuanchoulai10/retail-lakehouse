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
    gateway: ReadTableMetadataGateway, target_type: str, path: tuple[str, ...]
) -> PolicyTarget:
    """Build the target a request names, which must exist in the catalog.

    A table target takes its uuid from the catalog, and a missing table, namespace or catalog is
    NotFoundError; a catalog or namespace may hold no table. A catalog the platform's credential
    cannot read raises CatalogAccessDeniedError, untouched. A namespace level holding a dot is
    ValidationError: a table names its namespace dot-joined, so its namespaces are found by splitting
    on the dots, and a policy attached to such a level would never apply to any table.
    """
    with translate_domain_errors():
        kind = PolicyTargetType(target_type)
        if kind == PolicyTargetType.TABLE and len(path) < 3:  # noqa: PLR2004
            raise ValueError("a table target path is catalog, namespace levels and table name")
        if kind == PolicyTargetType.NAMESPACE:
            _refuse_dotted_levels(path[1:])
        if kind != PolicyTargetType.TABLE:
            target = PolicyTarget(type=kind, path=path)
    if kind == PolicyTargetType.TABLE:
        ref = TableMetadataRef(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1])
        try:
            table = gateway.load_table(ref)
        except CatalogNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        if table is None:
            raise NotFoundError(f"table {'.'.join(path)} not found")
        with translate_domain_errors():
            return PolicyTarget(type=kind, path=path, table_uuid=table.table_uuid)
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


def _refuse_dotted_levels(levels: tuple[str, ...]) -> None:
    for level in levels:
        if "." in level:
            msg = (
                f"namespace level {level!r} holds a '.': a table names its namespace dot-joined, "
                "so a policy attached there would never apply"
            )
            raise ValueError(msg)
