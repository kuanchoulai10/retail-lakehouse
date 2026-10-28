"""Test the table maintenance preset use case services."""

from __future__ import annotations

import pytest

from application.domain.model.table_discovery_rule.table_discovery_rule import (
    TableDiscoveryRule,
)
from application.domain.model.table_discovery_rule.table_discovery_rule_id import (
    TableDiscoveryRuleId,
)
from application.domain.model.table_discovery_rule.rule_effect import RuleEffect
from application.domain.model.table_discovery_rule.table_pattern import TablePattern
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.maintenance_settings.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from application.domain.model.table_maintenance_preset.table_maintenance_preset import (
    TableMaintenancePreset,
)
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table_maintenance_preset.create_table_maintenance_preset import (
    CreateTableMaintenancePresetUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.delete_table_maintenance_preset import (
    DeleteTableMaintenancePresetUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.get_table_maintenance_preset import (
    GetTableMaintenancePresetUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.list_table_maintenance_presets import (
    ListTableMaintenancePresetsUseCaseInput,
)
from application.port.inbound.table_maintenance_preset.update_table_maintenance_preset import (
    UpdateTableMaintenancePresetUseCaseInput,
)
from application.service.maintenance_settings.maintenance_settings_to_dict import (
    maintenance_settings_to_dict,
)
from application.service.table_maintenance_preset.create_table_maintenance_preset import (
    CreateTableMaintenancePresetService,
)
from application.service.table_maintenance_preset.delete_table_maintenance_preset import (
    DeleteTableMaintenancePresetService,
)
from application.service.table_maintenance_preset.get_table_maintenance_preset import (
    GetTableMaintenancePresetService,
)
from application.service.table_maintenance_preset.list_table_maintenance_presets import (
    ListTableMaintenancePresetsService,
)
from application.service.table_maintenance_preset.update_table_maintenance_preset import (
    UpdateTableMaintenancePresetService,
)


def _seed(repo, name="gold", tid="t-1", now=None, settings=None):
    from tests.application.service.conftest import NOW

    preset = TableMaintenancePreset.create(
        TableMaintenancePresetId(tid),
        name,
        settings or MaintenanceSettings(),
        now or NOW,
    )
    repo.create(preset)
    return preset


def test_create_preset_stores_and_returns_dict(presets_repo, clock, new_id, now):
    service = CreateTableMaintenancePresetService(
        presets_repo, clock=clock, new_id=new_id
    )
    out = service.execute(
        CreateTableMaintenancePresetUseCaseInput(
            name="gold", settings={"reconcile_interval_seconds": 600}
        )
    )
    assert out.id == "id-1"
    assert out.name == "gold"
    assert out.settings["reconcile_interval_seconds"] == 600
    assert out.created_at == now
    stored = presets_repo.get(TableMaintenancePresetId("id-1"))
    assert stored is not None
    assert stored.settings.reconcile_interval.total_seconds() == 600


def test_create_preset_duplicate_name_conflicts(presets_repo, clock, new_id):
    _seed(presets_repo)
    service = CreateTableMaintenancePresetService(
        presets_repo, clock=clock, new_id=new_id
    )
    with pytest.raises(ConflictError):
        service.execute(CreateTableMaintenancePresetUseCaseInput(name="gold"))


@pytest.mark.parametrize("name", ["", "   "])
def test_create_preset_blank_name_is_invalid(presets_repo, clock, new_id, name):
    service = CreateTableMaintenancePresetService(
        presets_repo, clock=clock, new_id=new_id
    )
    with pytest.raises(ValidationError):
        service.execute(CreateTableMaintenancePresetUseCaseInput(name=name))


def test_create_preset_unknown_setting_is_invalid(presets_repo, clock, new_id):
    service = CreateTableMaintenancePresetService(
        presets_repo, clock=clock, new_id=new_id
    )
    with pytest.raises(ValidationError):
        service.execute(
            CreateTableMaintenancePresetUseCaseInput(name="x", settings={"bogus": 1})
        )


def test_update_preset_renames_and_replaces_settings(presets_repo, clock):
    _seed(
        presets_repo,
        settings=MaintenanceSettings(
            rewrite_data_files=RewriteDataFilesSettings(min_reducible_files=9)
        ),
    )
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    out = service.execute(
        UpdateTableMaintenancePresetUseCaseInput(
            id="t-1",
            name="platinum",
            settings={"expire_snapshots": {"retain_last": 3}},
        )
    )
    assert out.name == "platinum"
    assert out.settings["expire_snapshots"]["retain_last"] == 3
    assert out.settings["rewrite_data_files"]["min_reducible_files"] == 5
    stored = presets_repo.get(TableMaintenancePresetId("t-1"))
    assert stored is not None
    assert stored.settings.rewrite_data_files.min_reducible_files == 5


def test_update_preset_keeps_omitted_fields(presets_repo, clock):
    seeded = _seed(presets_repo)
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    out = service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-1"))
    assert out.name == "gold"
    assert out.settings == maintenance_settings_to_dict(seeded.settings)


def test_update_preset_name_taken_by_other_conflicts(presets_repo, clock):
    _seed(presets_repo)
    _seed(presets_repo, name="silver", tid="t-2")
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    with pytest.raises(ConflictError):
        service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-2", name="gold"))


def test_update_preset_same_name_is_allowed(presets_repo, clock):
    _seed(presets_repo)
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    out = service.execute(
        UpdateTableMaintenancePresetUseCaseInput(id="t-1", name="gold")
    )
    assert out.name == "gold"


def test_update_unknown_preset_not_found(presets_repo, clock):
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    with pytest.raises(NotFoundError):
        service.execute(UpdateTableMaintenancePresetUseCaseInput(id="nope", name="x"))


def test_update_preset_blank_name_is_invalid(presets_repo, clock):
    _seed(presets_repo)
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    with pytest.raises(ValidationError):
        service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-1", name=" "))


def test_delete_preset_removes_it(presets_repo, rules_repo):
    _seed(presets_repo)
    DeleteTableMaintenancePresetService(presets_repo, rules_repo).execute(
        DeleteTableMaintenancePresetUseCaseInput(id="t-1")
    )
    assert presets_repo.get(TableMaintenancePresetId("t-1")) is None


def test_delete_preset_in_use_conflicts(presets_repo, rules_repo, now):
    _seed(presets_repo)
    rules_repo.create(
        TableDiscoveryRule.create(
            TableDiscoveryRuleId("r-1"),
            10,
            RuleEffect.INCLUDE,
            TablePattern(),
            TableMaintenancePresetId("t-1"),
            True,
            now,
        )
    )
    with pytest.raises(ConflictError):
        DeleteTableMaintenancePresetService(presets_repo, rules_repo).execute(
            DeleteTableMaintenancePresetUseCaseInput(id="t-1")
        )
    assert presets_repo.get(TableMaintenancePresetId("t-1")) is not None


def test_delete_unknown_preset_not_found(presets_repo, rules_repo):
    with pytest.raises(NotFoundError):
        DeleteTableMaintenancePresetService(presets_repo, rules_repo).execute(
            DeleteTableMaintenancePresetUseCaseInput(id="nope")
        )


def test_list_presets(presets_repo):
    _seed(presets_repo, name="b", tid="t-2")
    _seed(presets_repo, name="a", tid="t-1")
    out = ListTableMaintenancePresetsService(presets_repo).execute(
        ListTableMaintenancePresetsUseCaseInput()
    )
    assert [i.name for i in out.items] == ["a", "b"]


def test_get_preset(presets_repo):
    _seed(presets_repo)
    out = GetTableMaintenancePresetService(presets_repo).execute(
        GetTableMaintenancePresetUseCaseInput(id="t-1")
    )
    assert out.name == "gold"


def test_get_unknown_preset_not_found(presets_repo):
    with pytest.raises(NotFoundError):
        GetTableMaintenancePresetService(presets_repo).execute(
            GetTableMaintenancePresetUseCaseInput(id="nope")
        )
