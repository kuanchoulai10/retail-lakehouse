"""Define the policy_template_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from application.service.maintenance_settings.maintenance_settings_to_dict import (
    maintenance_settings_to_dict,
)

if TYPE_CHECKING:
    from application.domain.model.policy_template.policy_template import PolicyTemplate


def policy_template_output_fields(template: PolicyTemplate) -> dict[str, Any]:
    """Return the primitive fields shared by every policy template output."""
    return {
        "id": template.id.value,
        "name": template.name,
        "settings": maintenance_settings_to_dict(template.settings),
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }
