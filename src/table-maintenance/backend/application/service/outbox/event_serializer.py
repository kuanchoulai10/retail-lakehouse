"""Define the EventSerializer for outbox persistence."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import fields
from datetime import datetime
from typing import Any, ClassVar

from base.domain_event import DomainEvent

from application.domain.model.job.cron_expression import CronExpression
from application.domain.model.job.events import (
    JobArchived,
    JobCreated,
    JobPaused,
    JobResumed,
    JobTriggered,
    JobUpdated,
)
from application.domain.model.job.field_change import FieldChange
from application.domain.model.job.job_id import JobId
from application.domain.model.job.job_type import JobType
from application.domain.model.job.table_reference import TableReference
from application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.trigger_type import TriggerType
from application.domain.model.outbox_entry import OutboxEntry


class EventSerializer:
    """Serialize and deserialize domain events to/from JSON for outbox storage."""

    _REGISTRY: ClassVar[dict[str, type[DomainEvent]]] = {
        "JobCreated": JobCreated,
        "JobUpdated": JobUpdated,
        "JobPaused": JobPaused,
        "JobResumed": JobResumed,
        "JobArchived": JobArchived,
        "JobTriggered": JobTriggered,
        "JobRunCreated": JobRunCreated,
        "JobRunStarted": JobRunStarted,
        "JobRunCompleted": JobRunCompleted,
        "JobRunFailed": JobRunFailed,
        "JobRunCancelled": JobRunCancelled,
    }

    def serialize(self, event: DomainEvent) -> str:
        """Convert a domain event to a JSON string."""
        raw = {}
        for f in fields(event):
            if f.name == "occurred_at":
                continue
            raw[f.name] = getattr(event, f.name)
        return json.dumps(raw, default=self._json_default)

    def deserialize(self, event_type: str, payload: str) -> DomainEvent:
        """Reconstruct a domain event from its type name and JSON payload."""
        cls = self._REGISTRY[event_type]
        data = json.loads(payload)
        return self._reconstruct(cls, data)

    def to_outbox_entries(
        self,
        events: Sequence[DomainEvent],
        aggregate_type: str,
        aggregate_id: str,
    ) -> list[OutboxEntry]:
        """Convert domain events to outbox entries ready for persistence."""
        return [
            OutboxEntry(
                id=str(uuid.uuid4()),
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=type(event).__name__,
                payload=self.serialize(event),
                occurred_at=event.occurred_at,
            )
            for event in events
        ]

    @staticmethod
    def _json_default(obj: object) -> object:
        """Handle domain types during JSON serialization."""
        if isinstance(obj, TableReference):
            return {"catalog": obj.catalog, "table": obj.table}
        if isinstance(obj, FieldChange):
            return {
                "field": obj.field,
                "old_value": obj.old_value,
                "new_value": obj.new_value,
            }
        if isinstance(obj, CronExpression):
            return obj.expression
        if isinstance(obj, tuple):
            return [EventSerializer._json_default(item) for item in obj]
        if hasattr(obj, "value"):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Cannot serialize {type(obj)}")

    def _reconstruct(self, cls: type[DomainEvent], data: dict) -> DomainEvent:
        """Reconstruct a domain event from raw dict, rebuilding domain types."""
        field_types = {f.name: f.type for f in fields(cls) if f.name != "occurred_at"}
        kwargs = {}
        for name, value in data.items():
            if name == "occurred_at":
                continue
            kwargs[name] = self._rebuild_field(name, value, field_types.get(name))
        return cls(**kwargs)

    def _rebuild_field(self, name: str, value: Any, _type_hint: object) -> object:  # noqa: ANN401
        """Rebuild a single field value to its domain type."""
        if value is None:
            return None
        if name == "job_id":
            return JobId(value=value)
        if name == "run_id":
            return JobRunId(value=value)
        if name == "job_type":
            return JobType(value)
        if name == "trigger_type":
            return TriggerType(value)
        if name == "table_ref":
            return TableReference(catalog=value["catalog"], table=value["table"])
        if name == "cron":
            return CronExpression(expression=value) if value else None
        if name == "changes":
            return tuple(
                FieldChange(
                    field=c["field"], old_value=c["old_value"], new_value=c["new_value"]
                )
                for c in value
            )
        if name in ("started_at", "finished_at"):
            return datetime.fromisoformat(value) if isinstance(value, str) else value
        return value
