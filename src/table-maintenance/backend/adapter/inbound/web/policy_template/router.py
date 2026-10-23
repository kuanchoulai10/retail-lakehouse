"""Define the policy template router."""

from __future__ import annotations

from typing import Annotated

from adapter.inbound.web.policy_template.dto import (
    CreatePolicyTemplateApiRequest,
    PolicyTemplateApiResponse,
    UpdatePolicyTemplateApiRequest,
)
from adapter.inbound.web.use_cases_dependency import web_use_cases
from adapter.inbound.web.web_use_cases import WebUseCases
from application.port.inbound.policy_template.create_policy_template import (
    CreatePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.delete_policy_template import (
    DeletePolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.get_policy_template import (
    GetPolicyTemplateUseCaseInput,
)
from application.port.inbound.policy_template.list_policy_templates import (
    ListPolicyTemplatesUseCaseInput,
)
from application.port.inbound.policy_template.update_policy_template import (
    UpdatePolicyTemplateUseCaseInput,
)
from fastapi import APIRouter, Depends, Response, status

router = APIRouter(prefix="/policy-templates", tags=["policy-templates"])

UseCases = Annotated[WebUseCases, Depends(web_use_cases)]


@router.get("")
def list_policy_templates(use_cases: UseCases) -> list[PolicyTemplateApiResponse]:
    """List the policy templates."""
    output = use_cases.list_policy_templates.execute(ListPolicyTemplatesUseCaseInput())
    return [PolicyTemplateApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_policy_template(
    body: CreatePolicyTemplateApiRequest, use_cases: UseCases
) -> PolicyTemplateApiResponse:
    """Create a policy template."""
    output = use_cases.create_policy_template.execute(
        CreatePolicyTemplateUseCaseInput(name=body.name, settings=body.settings)
    )
    return PolicyTemplateApiResponse.model_validate(output)


@router.get("/{template_id}")
def get_policy_template(
    template_id: str, use_cases: UseCases
) -> PolicyTemplateApiResponse:
    """Return one policy template."""
    output = use_cases.get_policy_template.execute(
        GetPolicyTemplateUseCaseInput(id=template_id)
    )
    return PolicyTemplateApiResponse.model_validate(output)


@router.patch("/{template_id}")
def update_policy_template(
    template_id: str, body: UpdatePolicyTemplateApiRequest, use_cases: UseCases
) -> PolicyTemplateApiResponse:
    """Change the name or the settings of a policy template."""
    output = use_cases.update_policy_template.execute(
        UpdatePolicyTemplateUseCaseInput(
            id=template_id, name=body.name, settings=body.settings
        )
    )
    return PolicyTemplateApiResponse.model_validate(output)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy_template(template_id: str, use_cases: UseCases) -> Response:
    """Delete a policy template."""
    use_cases.delete_policy_template.execute(
        DeletePolicyTemplateUseCaseInput(id=template_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
