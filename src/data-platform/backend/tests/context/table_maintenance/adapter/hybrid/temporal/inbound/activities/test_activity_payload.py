"""Test that an activity payload is the same for a dataclass output and a UseCaseOutput."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from base import UseCaseOutput
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import activity_payload

RECORDED_AT = datetime(2026, 11, 18, 9, 30, tzinfo=UTC)


@dataclass(frozen=True)
class _CommitDataclass:
    """One commit, as a dataclass item."""

    snapshot_id: int
    committed_at: datetime
    summary: dict[str, str]


@dataclass(frozen=True)
class _CommitsDataclass:
    """The commits, as a dataclass output."""

    table_uuid: str
    recorded_at: datetime
    finished_at: datetime | None
    ratio: float
    writers: tuple[str, ...]
    commits: list[_CommitDataclass]


class _CommitsUseCaseOutput(UseCaseOutput):
    """The commits, as a UseCaseOutput with a nested class."""

    class Commit(UseCaseOutput):
        """One commit."""

        snapshot_id: int
        committed_at: datetime
        summary: dict[str, str]

    table_uuid: str
    recorded_at: datetime
    finished_at: datetime | None
    ratio: float
    writers: tuple[str, ...]
    commits: tuple[Commit, ...]


def test_activity_payload_matches_dataclass_payload() -> None:
    """The same values give identical dicts, datetimes written by ``isoformat`` with ``+00:00``."""
    dataclass_output = _CommitsDataclass(
        table_uuid="u",
        recorded_at=RECORDED_AT,
        finished_at=None,
        ratio=1,
        writers=("spark",),
        commits=[_CommitDataclass(snapshot_id=1, committed_at=RECORDED_AT, summary={"operation": "append"})],
    )
    model_output = _CommitsUseCaseOutput(
        table_uuid="u",
        recorded_at=RECORDED_AT,
        finished_at=None,
        ratio=1,
        writers=("spark",),
        commits=(
            _CommitsUseCaseOutput.Commit(snapshot_id=1, committed_at=RECORDED_AT, summary={"operation": "append"}),
        ),
    )

    payload = activity_payload(model_output)

    assert payload == activity_payload(dataclass_output)
    assert payload == {
        "table_uuid": "u",
        "recorded_at": "2026-11-18T09:30:00+00:00",
        "finished_at": None,
        "ratio": 1.0,
        "writers": ["spark"],
        "commits": [
            {"snapshot_id": 1, "committed_at": "2026-11-18T09:30:00+00:00", "summary": {"operation": "append"}},
        ],
    }


def test_a_float_field_set_from_an_int_is_a_float_on_the_wire() -> None:
    """A ``float`` field holds a float, so it is written ``1.0``, where a dataclass passed the int through as ``1``."""
    model_output = _CommitsUseCaseOutput(
        table_uuid="u", recorded_at=RECORDED_AT, finished_at=None, ratio=1, writers=(), commits=()
    )
    dataclass_output = _CommitsDataclass(
        table_uuid="u", recorded_at=RECORDED_AT, finished_at=None, ratio=1, writers=(), commits=[]
    )

    assert json.dumps(activity_payload(model_output)["ratio"]) == "1.0"
    assert json.dumps(activity_payload(dataclass_output)["ratio"]) == "1"
