"""Test PlatformApi, the scenarios' client for the table maintenance API."""

from __future__ import annotations

import json

import httpx
import pytest

from e2e.support import PlatformApi

DEFAULT = {
    "id": "mp-0",
    "name": "default",
    "is_default": True,
    "version": 1,
    "created_at": "2026-11-24T00:00:00Z",
    "updated_at": "2026-11-24T00:00:00Z",
    "description": "platform default",
    "on": {"schedule": {"every_seconds": 3600}},
    "dry_run": False,
    "rewrite_data_files": {"target": {"reducible_files": {"at_most": 5}}},
    "expire_snapshots": {"target": {}},
}


def _api(answer) -> tuple[PlatformApi, list[tuple[str, str, object]]]:
    seen: list[tuple[str, str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.raw_path.decode(), body))
        return answer(request.method, request.url.raw_path.decode())

    return PlatformApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="http://api")), seen


def test_a_maintenance_policy_starts_from_the_platform_default_with_the_changes_applied():
    """The default's own fields are dropped and the change sees and returns the rest."""

    def answer(method: str, path: str) -> httpx.Response:
        if method == "GET":
            return httpx.Response(200, json=DEFAULT)
        return httpx.Response(201, json={"name": "p", "id": "mp-1"})

    def change(body: dict) -> dict:
        del body["expire_snapshots"]
        return body | {"dry_run": True}

    api, seen = _api(answer)
    assert api.create_maintenance_policy("p", "e2e: p", change) == {"name": "p", "id": "mp-1"}
    assert seen[-1] == (
        "POST",
        "/v1/maintenance-policies",
        {
            "name": "p",
            "description": "e2e: p",
            "on": {"schedule": {"every_seconds": 3600}},
            "dry_run": True,
            "rewrite_data_files": {"target": {"reducible_files": {"at_most": 5}}},
        },
    )


def test_attaching_puts_the_target_and_returns_the_attachment_id():
    """Both kinds attach by PUT on the policy's attachments with a typed target."""
    api, seen = _api(lambda method, path: httpx.Response(200, json={"id": "pa-1"}))
    assert api.attach("maintenance-policies", "p", {"type": "table", "path": ["iceberg", "ns", "t"]}) == "pa-1"
    assert seen == [
        (
            "PUT",
            "/v1/maintenance-policies/p/attachments",
            {"target": {"type": "table", "path": ["iceberg", "ns", "t"]}},
        )
    ]


def test_a_refused_call_fails_naming_the_call_and_the_answer():
    """The scenario's failure says which call the API refused and what it answered."""
    api, _ = _api(lambda method, path: httpx.Response(422, json={"detail": "bad target"}))
    with pytest.raises(AssertionError, match=r"PUT /v1/discovery-policies/d/attachments answered 422: .*bad target"):
        api.attach("discovery-policies", "d", {"type": "namespace", "path": ["iceberg", "ns"]})


def test_a_table_is_found_by_its_place_in_the_catalog():
    """The uuid and status of the table at catalog, namespace and name, or None when the API has no such table."""
    tables = [
        {"uuid": "u-1", "catalog": "iceberg", "namespace": "ns", "table": "t", "status": "managed"},
        {"uuid": "u-2", "catalog": "iceberg", "namespace": "other", "table": "t", "status": "managed"},
    ]
    api, _ = _api(lambda method, path: httpx.Response(200, json=tables))
    assert api.table("iceberg", "ns", "t") == tables[0]
    assert api.table("iceberg", "ns", "missing") is None


def test_a_platform_setting_is_read_by_its_key():
    """Settings come in groups; the value of the one key is returned."""
    settings = {"groups": [{"items": [{"key": "a", "value": 1}]}, {"items": [{"key": "b", "value": 120}]}]}
    api, _ = _api(lambda method, path: httpx.Response(200, json=settings))
    assert api.platform_setting("b") == 120
