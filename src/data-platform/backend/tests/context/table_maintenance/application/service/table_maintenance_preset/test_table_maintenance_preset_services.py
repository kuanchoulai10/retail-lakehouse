"""Test the table maintenance preset use case services."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
    RewriteDataFilesSettings,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePreset,
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    CreateTableMaintenancePresetUseCaseInput,
    DeleteTableMaintenancePresetUseCaseInput,
    GetTableMaintenancePresetUseCaseInput,
    ListTableMaintenancePresetsUseCaseInput,
    UpdateTableMaintenancePresetUseCaseInput,
)
from context.table_maintenance.application.service.shared import (
    maintenance_settings_to_dict,
)
from context.table_maintenance.application.service.table_maintenance_preset import (
    CreateTableMaintenancePresetService,
    DeleteTableMaintenancePresetService,
    GetTableMaintenancePresetService,
    ListTableMaintenancePresetsService,
    UpdateTableMaintenancePresetService,
)


def _seed(repo, name="gold", tid="t-1", now=None, settings=None):
    from tests.context.table_maintenance.application.service.conftest import NOW

    preset = TableMaintenancePreset.create(
        TableMaintenancePresetId(tid),
        name,
        settings or MaintenanceSettings(),
        now or NOW,
    )
    repo.create(preset)
    return preset


def test_create_preset_stores_and_returns_dict(presets_repo, clock, new_id, now):
    """Creating a preset stores it and returns it with its settings as a dict."""
    service = CreateTableMaintenancePresetService(presets_repo, clock=clock, new_id=new_id)
    out = service.execute(
        CreateTableMaintenancePresetUseCaseInput(name="gold", settings={"reconcile_interval_seconds": 600})
    )
    assert out.id == "id-1"
    assert out.name == "gold"
    assert out.settings["reconcile_interval_seconds"] == 600
    assert out.created_at == now
    stored = presets_repo.get(TableMaintenancePresetId("id-1"))
    assert stored is not None
    assert stored.settings.reconcile_interval.total_seconds() == 600


def test_create_preset_duplicate_name_conflicts(presets_repo, clock, new_id):
    """Creating a preset with a name in use raises ConflictError."""
    _seed(presets_repo)
    service = CreateTableMaintenancePresetService(presets_repo, clock=clock, new_id=new_id)
    with pytest.raises(ConflictError):
        service.execute(CreateTableMaintenancePresetUseCaseInput(name="gold"))


@pytest.mark.parametrize("name", ["", "   "])
def test_create_preset_blank_name_is_invalid(presets_repo, clock, new_id, name):
    """Creating a preset with a blank name raises a ValidationError."""
    service = CreateTableMaintenancePresetService(presets_repo, clock=clock, new_id=new_id)
    with pytest.raises(ValidationError):
        service.execute(CreateTableMaintenancePresetUseCaseInput(name=name))


def test_create_preset_unknown_setting_is_invalid(presets_repo, clock, new_id):
    """Creating a preset with an unknown setting raises a ValidationError."""
    service = CreateTableMaintenancePresetService(presets_repo, clock=clock, new_id=new_id)
    with pytest.raises(ValidationError):
        service.execute(CreateTableMaintenancePresetUseCaseInput(name="x", settings={"bogus": 1}))


def test_update_preset_renames_and_replaces_settings(presets_repo, clock):
    """Updating a preset renames it and replaces its settings."""
    _seed(
        presets_repo,
        settings=MaintenanceSettings(rewrite_data_files=RewriteDataFilesSettings(min_reducible_files=9)),
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
    """Updating a preset keeps the fields the update leaves out."""
    seeded = _seed(presets_repo)
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    out = service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-1"))
    assert out.name == "gold"
    assert out.settings == maintenance_settings_to_dict(seeded.settings)


def test_update_preset_name_taken_by_other_conflicts(presets_repo, clock):
    """Renaming a preset to the name of another raises ConflictError."""
    _seed(presets_repo)
    _seed(presets_repo, name="silver", tid="t-2")
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    with pytest.raises(ConflictError):
        service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-2", name="gold"))


def test_update_preset_same_name_is_allowed(presets_repo, clock):
    """Updating a preset with its own name is allowed."""
    _seed(presets_repo)
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    out = service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-1", name="gold"))
    assert out.name == "gold"


def test_update_unknown_preset_not_found(presets_repo, clock):
    """Updating an unknown preset raises NotFoundError."""
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    with pytest.raises(NotFoundError):
        service.execute(UpdateTableMaintenancePresetUseCaseInput(id="nope", name="x"))


def test_update_preset_blank_name_is_invalid(presets_repo, clock):
    """Renaming a preset to a blank name raises a ValidationError."""
    _seed(presets_repo)
    service = UpdateTableMaintenancePresetService(presets_repo, clock=clock)
    with pytest.raises(ValidationError):
        service.execute(UpdateTableMaintenancePresetUseCaseInput(id="t-1", name=" "))


def test_delete_preset_removes_it(presets_repo, rules_repo):
    """Deleting an unused preset removes it."""
    _seed(presets_repo)
    DeleteTableMaintenancePresetService(presets_repo, rules_repo).execute(
        DeleteTableMaintenancePresetUseCaseInput(id="t-1")
    )
    assert presets_repo.get(TableMaintenancePresetId("t-1")) is None


def test_delete_preset_in_use_conflicts(presets_repo, rules_repo, now):
    """Deleting a preset that discovery rules use raises ConflictError and keeps it."""
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
    """Deleting an unknown preset raises NotFoundError."""
    with pytest.raises(NotFoundError):
        DeleteTableMaintenancePresetService(presets_repo, rules_repo).execute(
            DeleteTableMaintenancePresetUseCaseInput(id="nope")
        )


def test_list_presets(presets_repo):
    """Listing returns the presets."""
    _seed(presets_repo, name="b", tid="t-2")
    _seed(presets_repo, name="a", tid="t-1")
    out = ListTableMaintenancePresetsService(presets_repo).execute(ListTableMaintenancePresetsUseCaseInput())
    assert [i.name for i in out.items] == ["a", "b"]


def test_get_preset(presets_repo):
    """Getting a preset returns it by id."""
    _seed(presets_repo)
    out = GetTableMaintenancePresetService(presets_repo).execute(GetTableMaintenancePresetUseCaseInput(id="t-1"))
    assert out.name == "gold"


def test_get_unknown_preset_not_found(presets_repo):
    """Getting an unknown preset raises NotFoundError."""
    with pytest.raises(NotFoundError):
        GetTableMaintenancePresetService(presets_repo).execute(GetTableMaintenancePresetUseCaseInput(id="nope"))
