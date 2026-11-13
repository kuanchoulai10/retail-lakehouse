"""Define the CompactionRoundRowMapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.compaction_round import (
    CompactionRound,
    CompactionRoundId,
    RoundPick,
    RoundSkip,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping


class CompactionRoundRowMapper:
    """Map a CompactionRound to its row and back; picks and skips are stored as JSON, in their wire form."""

    @staticmethod
    def to_values(round_: CompactionRound) -> dict[str, Any]:
        """Return the column values of the round's row."""
        return {
            "id": round_.id.value,
            "started_at": round_.started_at,
            "budget_gb_hours": round_.budget_gb_hours,
            "used_gb_hours": round_.used_gb_hours,
            "picks_json": [p.to_primitives() for p in round_.picks],
            "skips_json": [s.to_primitives() for s in round_.skips],
            "skipped_total": round_.skipped_total,
            "busy_skipped": round_.busy_skipped,
        }

    @staticmethod
    def to_aggregate(row: RowMapping) -> CompactionRound:
        """Rebuild the round from its row."""
        return CompactionRound(
            id=CompactionRoundId(row["id"]),
            started_at=row["started_at"],
            budget_gb_hours=float(row["budget_gb_hours"]),
            used_gb_hours=float(row["used_gb_hours"]),
            picks=tuple(RoundPick.from_primitives(p) for p in row["picks_json"]),
            skips=tuple(RoundSkip.from_primitives(s) for s in row["skips_json"]),
            skipped_total=row["skipped_total"],
            busy_skipped=row["busy_skipped"],
        )
