"""Test the policy template routes."""

from __future__ import annotations

from typing import Any

from application.port.inbound.policy_template.create_policy_template import (
    CreatePolicyTemplateUseCaseInput,
    CreatePolicyTemplateUseCaseOutput,
)
from application.port.inbound.policy_template.delete_policy_template import (
    DeletePolicyTemplateUseCaseInput,
    DeletePolicyTemplateUseCaseOutput,
)
from application.port.inbound.policy_template.get_policy_template import (
    GetPolicyTemplateUseCaseInput,
    GetPolicyTemplateUseCaseOutput,
)
from application.port.inbound.policy_template.list_policy_templates import (
    ListPolicyTemplatesUseCaseOutput,
    ListPolicyTemplatesUseCaseOutputItem,
)
from application.port.inbound.policy_template.update_policy_template import (
    UpdatePolicyTemplateUseCaseInput,
    UpdatePolicyTemplateUseCaseOutput,
)
from tests.adapter.inbound.web.web_test_support import NOW, StubUseCase, build_client

FIELDS: dict[str, Any] = {
    "id": "t-1",
    "name": "gold",
    "settings": {"reconcile_interval_seconds": 3600},
    "created_at": NOW,
    "updated_at": NOW,
}


def test_list_policy_templates() -> None:
    output = ListPolicyTemplatesUseCaseOutput(
        items=[ListPolicyTemplatesUseCaseOutputItem(**FIELDS)]
    )
    client = build_client(list_policy_templates=StubUseCase(output))

    response = client.get("/v1/policy-templates")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "gold"


def test_create_policy_template_returns_201() -> None:
    stub = StubUseCase(CreatePolicyTemplateUseCaseOutput(**FIELDS))
    client = build_client(create_policy_template=stub)

    response = client.post(
        "/v1/policy-templates",
        json={"name": "gold", "settings": {"reconcile_interval_seconds": 3600}},
    )

    assert response.status_code == 201
    assert response.json()["settings"] == {"reconcile_interval_seconds": 3600}
    assert stub.requests == [
        CreatePolicyTemplateUseCaseInput(
            name="gold", settings={"reconcile_interval_seconds": 3600}
        )
    ]


def test_get_policy_template() -> None:
    stub = StubUseCase(GetPolicyTemplateUseCaseOutput(**FIELDS))
    client = build_client(get_policy_template=stub)

    response = client.get("/v1/policy-templates/t-1")

    assert response.status_code == 200
    assert stub.requests == [GetPolicyTemplateUseCaseInput(id="t-1")]


def test_update_policy_template_keeps_omitted_fields_unset() -> None:
    stub = StubUseCase(UpdatePolicyTemplateUseCaseOutput(**FIELDS))
    client = build_client(update_policy_template=stub)

    response = client.patch("/v1/policy-templates/t-1", json={"name": "platinum"})

    assert response.status_code == 200
    assert stub.requests == [
        UpdatePolicyTemplateUseCaseInput(id="t-1", name="platinum", settings=None)
    ]


def test_delete_policy_template_returns_204() -> None:
    stub = StubUseCase(DeletePolicyTemplateUseCaseOutput())
    client = build_client(delete_policy_template=stub)

    response = client.delete("/v1/policy-templates/t-1")

    assert response.status_code == 204
    assert stub.requests == [DeletePolicyTemplateUseCaseInput(id="t-1")]
