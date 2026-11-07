"""Define the JobRequest parsed from GLAC_REQUEST."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

OPERATIONS = (
    "rewrite_data_files",
    "rewrite_manifests",
    "expire_snapshots",
    "remove_orphan_files",
)


@dataclass(frozen=True)
class JobRequest:
    """Carry the submit gateway input of one maintenance job."""

    app_name: str
    run_id: str
    operation: str
    attempt: int
    catalog: str
    namespace: str
    table: str
    callback_url: str
    where: list[str] = field(default_factory=list)
    procedure_args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, raw: str) -> JobRequest:
        """Parse the JSON document; unknown keys are ignored."""
        data = json.loads(raw)
        return cls(
            app_name=data.get("app_name", ""),
            run_id=data["run_id"],
            operation=data["operation"],
            attempt=int(data["attempt"]),
            catalog=data["catalog"],
            namespace=data["namespace"],
            table=data["table"],
            callback_url=data["callback_url"],
            where=list(data.get("where") or []),
            procedure_args=dict(data.get("procedure_args") or {}),
        )
