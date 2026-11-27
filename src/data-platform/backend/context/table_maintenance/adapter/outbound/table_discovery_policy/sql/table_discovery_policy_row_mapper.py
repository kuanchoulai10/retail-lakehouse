"""Define the TableDiscoveryPolicyRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyId,
    TableDiscoveryPolicyName,
    TableDiscoveryPolicyVersion,
    TableNamePattern,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


def _encode_content(description: str, rules: DiscoveryRules) -> dict[str, Any]:
    """Return a version's content as stored: its description and its rules in order."""
    return {
        "description": description,
        "rules": [
            {"action": rule.action.value, "table_name_pattern": rule.table_name_pattern.value} for rule in rules.rules
        ],
    }


def _decode_rules(content: dict[str, Any]) -> DiscoveryRules:
    return DiscoveryRules(
        rules=tuple(
            DiscoveryRule(
                action=RuleAction(rule["action"]),
                table_name_pattern=TableNamePattern(value=rule["table_name_pattern"]),
            )
            for rule in content["rules"]
        )
    )


class TableDiscoveryPolicyRowMapper:
    """Convert between TableDiscoveryPolicy aggregates and table rows."""

    @staticmethod
    def to_policy_values(policy: TableDiscoveryPolicy) -> dict[str, Any]:
        """Return the columns of the policy row."""
        return {
            "id": policy.id.value,
            "name": policy.name.value,
            "version": policy.version,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }

    @staticmethod
    def to_version_values(version: TableDiscoveryPolicyVersion) -> dict[str, Any]:
        """Return the columns of a version row; the description and rules are stored as one JSON document."""
        return {
            "policy_id": version.policy_id.value,
            "version": version.version,
            "content_json": _encode_content(version.description, version.rules),
            "created_at": version.created_at,
        }

    @staticmethod
    def to_aggregate(policy_row: RowMapping, version_row: RowMapping) -> TableDiscoveryPolicy:
        """Rebuild the aggregate from its policy row and its current version row."""
        content = version_row["content_json"]
        return TableDiscoveryPolicy(
            id=TableDiscoveryPolicyId(policy_row["id"]),
            name=TableDiscoveryPolicyName(value=policy_row["name"]),
            description=content["description"],
            rules=_decode_rules(content),
            version=policy_row["version"],
            created_at=policy_row["created_at"],
            updated_at=policy_row["updated_at"],
        )

    @staticmethod
    def to_version(row: RowMapping) -> TableDiscoveryPolicyVersion:
        """Rebuild a version record from a version row."""
        content = row["content_json"]
        return TableDiscoveryPolicyVersion(
            policy_id=TableDiscoveryPolicyId(row["policy_id"]),
            version=row["version"],
            description=content["description"],
            rules=_decode_rules(content),
            created_at=row["created_at"],
        )
