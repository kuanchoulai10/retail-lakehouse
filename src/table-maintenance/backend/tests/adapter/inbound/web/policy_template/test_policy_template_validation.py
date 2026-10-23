"""Test settings validation through the real policy template service."""

from __future__ import annotations

import pytest
from application.service.policy_template.create_policy_template import (
    CreatePolicyTemplateService,
)
from tests.adapter.inbound.web.web_test_support import build_client
from tests.fakes.in_memory_policy_templates_repo import InMemoryPolicyTemplatesRepo


@pytest.fixture
def client():
    service = CreatePolicyTemplateService(InMemoryPolicyTemplatesRepo())
    return build_client(create_policy_template=service)


def test_orphan_older_than_below_one_day_returns_422(client) -> None:
    response = client.post(
        "/v1/policy-templates",
        json={
            "name": "risky",
            "settings": {"remove_orphan_files": {"older_than_seconds": 3600}},
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_unknown_settings_key_returns_422(client) -> None:
    response = client.post(
        "/v1/policy-templates",
        json={"name": "typo", "settings": {"expire_snapshot": {"enabled": True}}},
    )

    assert response.status_code == 422


def test_valid_settings_are_created(client) -> None:
    response = client.post(
        "/v1/policy-templates",
        json={
            "name": "ok",
            "settings": {"remove_orphan_files": {"older_than_seconds": 172800}},
        },
    )

    assert response.status_code == 201
    orphan = response.json()["settings"]["remove_orphan_files"]
    assert orphan["older_than_seconds"] == 172800
