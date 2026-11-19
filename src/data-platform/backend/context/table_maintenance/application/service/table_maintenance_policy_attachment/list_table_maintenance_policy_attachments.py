"""Define the ListTableMaintenancePolicyAttachmentsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ListTableMaintenancePolicyAttachmentsUseCase,
    ListTableMaintenancePolicyAttachmentsUseCaseInput,
    ListTableMaintenancePolicyAttachmentsUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogNotFoundError,
    ReadTableMetadataGatewayListInput,
    TableId,
    TableMetadataRef,
    TableStatus,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    PolicyTargetType,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table_maintenance_policy_attachment.scope_target_in_listing import (  # noqa: E501
    scope_target_in_listing,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        PolicyTarget,
        TableMaintenancePolicyAttachmentsRepo,
    )


class ListTableMaintenancePolicyAttachmentsService(ListTableMaintenancePolicyAttachmentsUseCase):
    """List policy attachments, optionally only those of one policy, marking those left behind."""

    def __init__(
        self,
        policies_repo: TableMaintenancePoliciesRepo,
        attachments_repo: TableMaintenancePolicyAttachmentsRepo,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
    ) -> None:
        """Bind the repos and the catalog gateway."""
        self._policies_repo = policies_repo
        self._attachments_repo = attachments_repo
        self._gateway = gateway
        self._tables_repo = tables_repo

    def execute(
        self, request: ListTableMaintenancePolicyAttachmentsUseCaseInput
    ) -> ListTableMaintenancePolicyAttachmentsUseCaseOutput:
        """Return the attachments, each orphaned when its target left the catalog; an unknown policy is not found.

        The attachments and their policies are two reads: an attachment whose policy was detached
        and deleted in between has no policy left to name, so it is skipped.
        """
        if request.policy_name is None:
            attachments = self._attachments_repo.list_all()
        else:
            with translate_domain_errors():
                name = TableMaintenancePolicyName(value=request.policy_name)
            policy = self._policies_repo.get_by_name(name)
            if policy is None:
                raise NotFoundError(f"table maintenance policy {request.policy_name} not found")
            attachments = self._attachments_repo.list_for_policy(policy.id)
        names = {p.id.value: p.name.value for p in self._policies_repo.get_many([a.policy_id for a in attachments])}
        listings: dict[str, list[TableMetadataRef] | None] = {}
        return ListTableMaintenancePolicyAttachmentsUseCaseOutput(
            items=tuple(
                ListTableMaintenancePolicyAttachmentsUseCaseOutput.TableMaintenancePolicyAttachment(
                    type=a.target.type.value,
                    path=a.target.path,
                    table_uuid=a.target.table_uuid,
                    policy_id=a.policy_id.value,
                    policy_name=names[a.policy_id.value],
                    attached_at=a.attached_at,
                    orphaned=not self._in_catalog(a.target, listings),
                )
                for a in attachments
                if a.policy_id.value in names
            )
        )

    def _in_catalog(self, target: PolicyTarget, listings: dict[str, list[TableMetadataRef] | None]) -> bool:
        if target.type == PolicyTargetType.TABLE:
            return self._table_in_catalog(target)
        catalog = target.path[0]
        if catalog not in listings:
            listings[catalog] = self._list_tables(catalog)
        tables = listings[catalog]
        return tables is not None and scope_target_in_listing(target.type, target.path, tables)

    def _list_tables(self, catalog: str) -> list[TableMetadataRef] | None:
        try:
            return self._gateway.list_tables(ReadTableMetadataGatewayListInput(catalog=catalog))
        except CatalogNotFoundError:
            return None

    def _table_in_catalog(self, target: PolicyTarget) -> bool:
        """A table is in the catalog under its attached path, or under any name table maintenance knows it by."""
        table_uuid = target.table_uuid
        known = None if table_uuid is None else self._tables_repo.get(TableId(table_uuid))
        if known is not None and known.status != TableStatus.DROPPED:
            return True
        path = target.path
        try:
            loaded = self._gateway.load_table(
                TableMetadataRef(catalog=path[0], namespace=".".join(path[1:-1]), table=path[-1])
            )
        except CatalogNotFoundError:
            return False
        return loaded is not None and loaded.table_uuid == table_uuid
