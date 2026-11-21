"""Define the AttachTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class AttachTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Carry the attachment made: its ``pa-`` id, the target and the attached policy's ``mp-`` id and name."""

    id: str
    target_type: str
    path: tuple[str, ...]
    table_uuid: str | None
    policy_id: str
    policy_name: str
    attached_at: datetime
