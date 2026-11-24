"""Test reconcile_now, which asks for a check and returns the record it made."""

from __future__ import annotations

import httpx
import pytest

from e2e.support import PlatformApi, reconcile_now

UUID = "00000000-0000-4000-8000-000000000001"
OLD = {"reconciliation_id": "rc-old", "wake_reasons": {"reconcile_now": 1}}
SCHEDULED = {"reconciliation_id": "rc-sched", "wake_reasons": {"schedule": 1}}
NEW = {"reconciliation_id": "rc-new", "wake_reasons": {"reconcile_now": 1}}


def _platform(after_post: list[dict]) -> tuple[PlatformApi, list[str]]:
    seen: list[str] = []
    state = {"posted": False}

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}")
        if request.method == "POST":
            state["posted"] = True
            return httpx.Response(202, json={})
        return httpx.Response(200, json=[OLD, *after_post] if state["posted"] else [OLD])

    return PlatformApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="http://api")), seen


def test_the_new_reconcile_now_record_answers():
    """A record from before the post, or one another trigger made, never answers."""
    platform, seen = _platform([SCHEDULED, NEW])
    assert reconcile_now(platform, UUID) == NEW
    assert seen[:2] == [f"GET /v1/tables/{UUID}/reconciliations", f"POST /v1/tables/{UUID}/reconcile"]


def test_no_new_record_times_out_naming_the_table():
    """Without the record the wait ends at its bound and says which table it waited for."""
    platform, _ = _platform([SCHEDULED])
    with pytest.raises(TimeoutError, match=f"reconcile-now record of {UUID}"):
        reconcile_now(platform, UUID, timeout=0.2)
