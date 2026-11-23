"""Define the run_api_response function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.adapter.inbound.web.table_maintenance_run.dto import (
    TableMaintenanceRunApiResponse,
    TableMaintenanceRunPartitionFieldApiResponse,
    TableMaintenanceRunPartitionSpecApiResponse,
)
from context.table_maintenance.adapter.inbound.web.table_maintenance_run.partition_value_text import (
    partition_value_text,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        GetTableMaintenanceRunUseCaseOutput,
        ListTableMaintenanceRunsUseCaseOutput,
    )


def run_api_response(
    run: GetTableMaintenanceRunUseCaseOutput | ListTableMaintenanceRunsUseCaseOutput.TableMaintenanceRun,
) -> TableMaintenanceRunApiResponse:
    """Return the API view of a run: its job content shown as settings and partitions."""
    content = dict(run.content)
    content.pop("operation", None)
    selections = content.pop("partitions", [])
    settings = {**{key: value for key, value in content.items() if key != "options"}, **content.get("options", {})}
    return TableMaintenanceRunApiResponse.model_validate(
        {
            **run.model_dump(exclude={"content"}),
            "settings": settings,
            "partitions": [_spec_view(selection) for selection in selections],
        }
    )


def _spec_view(selection: dict[str, Any]) -> TableMaintenanceRunPartitionSpecApiResponse:
    shown = [index for index, field in enumerate(selection["spec"]["fields"]) if field["transform"] != "void"]
    fields = [selection["spec"]["fields"][index] for index in shown]
    return TableMaintenanceRunPartitionSpecApiResponse(
        spec_id=selection["spec"]["spec_id"],
        fields=[
            TableMaintenanceRunPartitionFieldApiResponse(column=field["source_column"], transform=field["transform"])
            for field in fields
        ],
        partitions=[
            [
                partition_value_text(field["transform"], field["source_type"], values[index])
                for index, field in zip(shown, fields, strict=True)
            ]
            for values in selection["values"]
        ],
    )
