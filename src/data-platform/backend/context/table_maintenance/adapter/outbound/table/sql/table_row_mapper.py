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
    DiscoveryMatch,
    MaintenanceOperation,
    OperationState,
    OverTargetPartition,
    RecordedAttempt,
    Table,
    TableDiscoveryPolicyId,
    TableDiscoveryRuleId,
    TableId,
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
    TableName,
    TablePriority,
    TableStatus,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import RowMapping

_ATTENTION_POLICY_KEYS = frozenset({"id", "version", "target", "name"})


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
    if not isinstance(policy, dict) or not _ATTENTION_POLICY_KEYS <= policy.keys():
        found = sorted(policy) if isinstance(policy, dict) else type(policy).__name__
        msg = (
            'an attention mark\'s policy must be {"id", "version", "target", "name"} (an mp- id and the '
            f"policy's name when the mark was set); found {found}, a mark from before policies had ids"
        )
        raise ValueError(msg)
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


def _decode_discovered_by(row: RowMapping) -> DiscoveryMatch:
    """Return the match a row stored, or the platform default's for a row stored before matches were."""
    policy_id = row["matched_policy_id"]
    if policy_id is None:
        return DiscoveryMatch.platform_default()
    rule_id = row["matched_rule_id"]
    return DiscoveryMatch(
        policy_id=TableDiscoveryPolicyId(policy_id),
        policy_version=row["matched_policy_version"],
        rule_id=None if rule_id is None else TableDiscoveryRuleId(rule_id),
    )


def encode_over_target_partitions(partitions: Sequence[OverTargetPartition]) -> list[dict[str, Any]]:
    """Return the JSON form of the over-target partitions stored in the tables row."""
    return [
        {"spec_id": p.spec_id, "values": list(p.values), "since": IsoDatetimeCodec.encode(p.since)} for p in partitions
    ]


def _decode_over_target_partitions(data: list[dict[str, Any]] | None) -> tuple[OverTargetPartition, ...]:
    if data is None:
        return ()
    decoded = []
    for entry in data:
        since = IsoDatetimeCodec.decode(entry["since"])
        if since is None:
            msg = "an over-target partition needs its start time"
            raise ValueError(msg)
        decoded.append(OverTargetPartition(spec_id=entry["spec_id"], values=tuple(entry["values"]), since=since))
    return tuple(decoded)


class TableRowMapper:
    """Convert between Table aggregates and table rows."""

    @staticmethod
    def to_values(table: Table) -> dict[str, Any]:
        """Return the column values of the aggregate, without the over-target partitions its own write owns."""
        return {
            "uuid": table.id.value,
            "catalog": table.name.catalog,
            "namespace": table.name.namespace,
            "table_name": table.name.table,
            "status": table.status.value,
            "matched_rule_id": (None if table.matched_rule_id is None else table.matched_rule_id.value),
            "matched_policy_id": table.discovered_by.policy_id.value,
            "matched_policy_version": table.discovered_by.policy_version,
            "registered_at": table.registered_at,
            "updated_at": table.updated_at,
            "operation_states_json": {op.value: _encode_state(state) for op, state in table.operation_states.items()},
            "last_committed_at": table.last_committed_at,
            "last_discovered_at": table.last_discovered_at,
            "priority": table.priority.value,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> Table:
        """Rebuild the aggregate from a row without registering events."""
        return Table(
            id=TableId(row["uuid"]),
            name=TableName(
                catalog=row["catalog"],
                namespace=row["namespace"],
                table=row["table_name"],
            ),
            status=TableStatus(row["status"]),
            discovered_by=_decode_discovered_by(row),
            registered_at=row["registered_at"],
            updated_at=row["updated_at"],
            operation_states={
                MaintenanceOperation(op): _decode_state(data) for op, data in row["operation_states_json"].items()
            },
            last_committed_at=row["last_committed_at"],
            last_discovered_at=row["last_discovered_at"],
            priority=TablePriority(row["priority"] or TablePriority.default()),
            over_target_partitions=_decode_over_target_partitions(row["over_target_partitions_json"]),
        )
