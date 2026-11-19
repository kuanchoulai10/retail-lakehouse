"""Define the TableRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.adapter.outbound.shared.sql import (
    IsoDatetimeCodec,
)
from context.table_maintenance.application.port.outbound.table import (
    AppliedPolicyRef,
    AttentionMark,
    ComputeSize,
    MaintenanceOperation,
    OperationState,
    RecordedAttempt,
    Table,
    TableDiscoveryRuleId,
    TableId,
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
    TableName,
    TableStatus,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


def _encode_attention(mark: AttentionMark | None) -> dict[str, Any] | None:
    if mark is None:
        return None
    return {
        "since": IsoDatetimeCodec.encode(mark.since),
        "reason": mark.reason,
        "policy": {
            "id": mark.policy.policy_id.value,
            "version": mark.policy.version,
            "target": mark.policy.target,
            "name": mark.policy_name.value,
        },
    }


def _decode_attention(data: dict[str, Any] | None) -> AttentionMark | None:
    if data is None:
        return None
    since = IsoDatetimeCodec.decode(data["since"])
    if since is None:
        msg = "an attention mark needs its start time"
        raise ValueError(msg)
    policy = data["policy"]
    return AttentionMark(
        since=since,
        reason=data["reason"],
        policy=AppliedPolicyRef(
            policy_id=TableMaintenancePolicyId(policy["id"]), version=policy["version"], target=policy["target"]
        ),
        policy_name=TableMaintenancePolicyName(value=policy["name"]),
    )


def _encode_recorded(attempt: RecordedAttempt | None) -> dict[str, Any] | None:
    return None if attempt is None else {"run_id": attempt.run_id, "attempt": attempt.attempt}


def _decode_recorded(data: dict[str, Any] | None) -> RecordedAttempt | None:
    return None if data is None else RecordedAttempt(run_id=data["run_id"], attempt=data["attempt"])


def _encode_state(state: OperationState) -> dict[str, Any]:
    return {
        "last_attempt_at": IsoDatetimeCodec.encode(state.last_attempt_at),
        "consecutive_failures": state.consecutive_failures,
        "last_successful_size": None if state.last_successful_size is None else state.last_successful_size.value,
        "attention": _encode_attention(state.attention),
        "low_use_successes": state.low_use_successes,
        "last_recorded": _encode_recorded(state.last_recorded),
    }


def _decode_state(data: dict[str, Any]) -> OperationState:
    size = data.get("last_successful_size")
    return OperationState(
        last_attempt_at=IsoDatetimeCodec.decode(data["last_attempt_at"]),
        consecutive_failures=data["consecutive_failures"],
        last_successful_size=None if size is None else ComputeSize(size),
        attention=_decode_attention(data.get("attention")),
        low_use_successes=data.get("low_use_successes", 0),
        last_recorded=_decode_recorded(data.get("last_recorded")),
    )


class TableRowMapper:
    """Convert between Table aggregates and table rows."""

    @staticmethod
    def to_values(table: Table) -> dict[str, Any]:
        """Return the column values of the aggregate."""
        return {
            "uuid": table.id.value,
            "catalog": table.name.catalog,
            "namespace": table.name.namespace,
            "table_name": table.name.table,
            "status": table.status.value,
            "matched_rule_id": (None if table.matched_rule_id is None else table.matched_rule_id.value),
            "registered_at": table.registered_at,
            "updated_at": table.updated_at,
            "operation_states_json": {op.value: _encode_state(state) for op, state in table.operation_states.items()},
            "last_committed_at": table.last_committed_at,
            "last_discovered_at": table.last_discovered_at,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> Table:
        """Rebuild the aggregate from a row without registering events."""
        matched = row["matched_rule_id"]
        return Table(
            id=TableId(row["uuid"]),
            name=TableName(
                catalog=row["catalog"],
                namespace=row["namespace"],
                table=row["table_name"],
            ),
            status=TableStatus(row["status"]),
            matched_rule_id=None if matched is None else TableDiscoveryRuleId(matched),
            registered_at=row["registered_at"],
            updated_at=row["updated_at"],
            operation_states={
                MaintenanceOperation(op): _decode_state(data) for op, data in row["operation_states_json"].items()
            },
            last_committed_at=row["last_committed_at"],
            last_discovered_at=row["last_discovered_at"],
        )
