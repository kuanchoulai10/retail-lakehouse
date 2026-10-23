"""Test the policy template use case services."""

from __future__ import annotations

import pytest

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.maintenance_settings.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from application.domain.model.policy_template.policy_template import PolicyTemplate
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError
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
from application.service.maintenance_settings.maintenance_settings_to_dict import (
    maintenance_settings_to_dict,
)
from application.service.policy_template.create_policy_template import (
    CreatePolicyTemplateService,
)
from application.service.policy_template.delete_policy_template import (
    DeletePolicyTemplateService,
)
from application.service.policy_template.get_policy_template import (
    GetPolicyTemplateService,
)
from application.service.policy_template.list_policy_templates import (
    ListPolicyTemplatesService,
)
from application.service.policy_template.update_policy_template import (
    UpdatePolicyTemplateService,
)


def _seed(repo, name="gold", tid="t-1", now=None, settings=None):
    from tests.application.service.conftest import NOW

    template = PolicyTemplate.create(
        PolicyTemplateId(tid), name, settings or MaintenanceSettings(), now or NOW
    )
    repo.create(template)
    return template


def test_create_template_stores_and_returns_dict(templates_repo, clock, new_id, now):
    service = CreatePolicyTemplateService(templates_repo, clock=clock, new_id=new_id)
    out = service.execute(
        CreatePolicyTemplateUseCaseInput(
            name="gold", settings={"reconcile_interval_seconds": 600}
        )
    )
    assert out.id == "id-1"
    assert out.name == "gold"
    assert out.settings["reconcile_interval_seconds"] == 600
    assert out.created_at == now
    stored = templates_repo.get(PolicyTemplateId("id-1"))
    assert stored is not None
    assert stored.settings.reconcile_interval.total_seconds() == 600


def test_create_template_duplicate_name_conflicts(templates_repo, clock, new_id):
    _seed(templates_repo)
    service = CreatePolicyTemplateService(templates_repo, clock=clock, new_id=new_id)
    with pytest.raises(ConflictError):
        service.execute(CreatePolicyTemplateUseCaseInput(name="gold"))


@pytest.mark.parametrize("name", ["", "   "])
def test_create_template_blank_name_is_invalid(templates_repo, clock, new_id, name):
    service = CreatePolicyTemplateService(templates_repo, clock=clock, new_id=new_id)
    with pytest.raises(ValidationError):
        service.execute(CreatePolicyTemplateUseCaseInput(name=name))


def test_create_template_unknown_setting_is_invalid(templates_repo, clock, new_id):
    service = CreatePolicyTemplateService(templates_repo, clock=clock, new_id=new_id)
    with pytest.raises(ValidationError):
        service.execute(
            CreatePolicyTemplateUseCaseInput(name="x", settings={"bogus": 1})
        )


def test_update_template_renames_and_replaces_settings(templates_repo, clock):
    _seed(
        templates_repo,
        settings=MaintenanceSettings(
            rewrite_data_files=RewriteDataFilesSettings(min_reducible_files=9)
        ),
    )
    service = UpdatePolicyTemplateService(templates_repo, clock=clock)
    out = service.execute(
        UpdatePolicyTemplateUseCaseInput(
            id="t-1",
            name="platinum",
            settings={"expire_snapshots": {"retain_last": 3}},
        )
    )
    assert out.name == "platinum"
    assert out.settings["expire_snapshots"]["retain_last"] == 3
    assert out.settings["rewrite_data_files"]["min_reducible_files"] == 5
    stored = templates_repo.get(PolicyTemplateId("t-1"))
    assert stored is not None
    assert stored.settings.rewrite_data_files.min_reducible_files == 5


def test_update_template_keeps_omitted_fields(templates_repo, clock):
    seeded = _seed(templates_repo)
    service = UpdatePolicyTemplateService(templates_repo, clock=clock)
    out = service.execute(UpdatePolicyTemplateUseCaseInput(id="t-1"))
    assert out.name == "gold"
    assert out.settings == maintenance_settings_to_dict(seeded.settings)


def test_update_template_name_taken_by_other_conflicts(templates_repo, clock):
    _seed(templates_repo)
    _seed(templates_repo, name="silver", tid="t-2")
    service = UpdatePolicyTemplateService(templates_repo, clock=clock)
    with pytest.raises(ConflictError):
        service.execute(UpdatePolicyTemplateUseCaseInput(id="t-2", name="gold"))


def test_update_template_same_name_is_allowed(templates_repo, clock):
    _seed(templates_repo)
    service = UpdatePolicyTemplateService(templates_repo, clock=clock)
    out = service.execute(UpdatePolicyTemplateUseCaseInput(id="t-1", name="gold"))
    assert out.name == "gold"


def test_update_unknown_template_not_found(templates_repo, clock):
    service = UpdatePolicyTemplateService(templates_repo, clock=clock)
    with pytest.raises(NotFoundError):
        service.execute(UpdatePolicyTemplateUseCaseInput(id="nope", name="x"))


def test_update_template_blank_name_is_invalid(templates_repo, clock):
    _seed(templates_repo)
    service = UpdatePolicyTemplateService(templates_repo, clock=clock)
    with pytest.raises(ValidationError):
        service.execute(UpdatePolicyTemplateUseCaseInput(id="t-1", name=" "))


def test_delete_template_removes_it(templates_repo, rules_repo):
    _seed(templates_repo)
    DeletePolicyTemplateService(templates_repo, rules_repo).execute(
        DeletePolicyTemplateUseCaseInput(id="t-1")
    )
    assert templates_repo.get(PolicyTemplateId("t-1")) is None


def test_delete_template_in_use_conflicts(templates_repo, rules_repo, now):
    _seed(templates_repo)
    rules_repo.create(
        DiscoveryRule.create(
            DiscoveryRuleId("r-1"),
            10,
            RuleEffect.INCLUDE,
            TablePattern(),
            PolicyTemplateId("t-1"),
            True,
            now,
        )
    )
    with pytest.raises(ConflictError):
        DeletePolicyTemplateService(templates_repo, rules_repo).execute(
            DeletePolicyTemplateUseCaseInput(id="t-1")
        )
    assert templates_repo.get(PolicyTemplateId("t-1")) is not None


def test_delete_unknown_template_not_found(templates_repo, rules_repo):
    with pytest.raises(NotFoundError):
        DeletePolicyTemplateService(templates_repo, rules_repo).execute(
            DeletePolicyTemplateUseCaseInput(id="nope")
        )


def test_list_templates(templates_repo):
    _seed(templates_repo, name="b", tid="t-2")
    _seed(templates_repo, name="a", tid="t-1")
    out = ListPolicyTemplatesService(templates_repo).execute(
        ListPolicyTemplatesUseCaseInput()
    )
    assert [i.name for i in out.items] == ["a", "b"]


def test_get_template(templates_repo):
    _seed(templates_repo)
    out = GetPolicyTemplateService(templates_repo).execute(
        GetPolicyTemplateUseCaseInput(id="t-1")
    )
    assert out.name == "gold"


def test_get_unknown_template_not_found(templates_repo):
    with pytest.raises(NotFoundError):
        GetPolicyTemplateService(templates_repo).execute(
            GetPolicyTemplateUseCaseInput(id="nope")
        )
