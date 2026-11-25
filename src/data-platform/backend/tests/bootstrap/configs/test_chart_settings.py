"""Test that the wave-25 chart writes every setting each role reads, generic ones at the backend's defaults."""

from __future__ import annotations

import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pydantic import BaseModel

from bootstrap.configs import (
    ApiSettings,
    EventConsumerSettings,
    MigrateSettings,
    WorkerSettings,
    load_role_settings,
    setting_paths,
)

if TYPE_CHECKING:
    from bootstrap.configs import RoleSettings

CHART = Path(__file__).resolve().parents[6] / "platform" / "25-lakehouse-control-plane" / "chart"
ROLES: dict[str, type[RoleSettings]] = {
    "api": ApiSettings,
    "worker": WorkerSettings,
    "event-consumer": EventConsumerSettings,
    "migrate": MigrateSettings,
}
NOT_IN_THE_FILE = {
    ("database", "sqlite", "path"),
}
SET_BY_THE_ENVIRONMENT_OR_THE_CHART = {
    ("callback_base_url",),
    ("catalog", "uri"),
    ("catalog", "management_uri"),
    ("catalog", "s3_endpoint"),
    ("catalog", "s3_region"),
    ("database", "backend"),
    ("http", "root_path"),
    ("kafka", "bootstrap_servers"),
    ("kafka", "topic"),
    ("metrics", "prometheus_url"),
    ("spark", "catalog_credential_secret"),
    ("spark", "event_log_dir"),
    ("spark", "image"),
    ("spark", "image_pull_policy"),
    ("spark", "namespace"),
    ("spark", "s3_secret_name"),
    ("spark", "service_account"),
    ("spark", "volcano", "priority_class_prefix"),
    ("spark", "volcano", "queue"),
    ("spark", "volcano", "urgent_queue"),
    ("temporal", "address"),
}

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm renders the chart")


@pytest.fixture(scope="module")
def settings_files() -> dict[str, dict[str, Any]]:
    """Return each role's settings file as the chart writes it for a whole environment."""
    rendered = subprocess.run(
        [
            "helm",
            "template",
            "table-maintenance",
            str(CHART),
            "--namespace",
            "lakehouse-control-plane",
            "--values",
            str(CHART / "ci" / "default-values.yaml"),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {
        doc["metadata"]["name"].removeprefix("table-maintenance-").removesuffix("-config"): yaml.safe_load(
            doc["data"]["config.yaml"]
        )
        for doc in yaml.safe_load_all(rendered)
        if doc and doc["kind"] == "ConfigMap"
    }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.upper().startswith("GLAC_"):
            monkeypatch.delenv(name)


def _leaves(node: dict[str, Any], prefix: tuple[str, ...] = ()) -> dict[tuple[str, ...], Any]:
    leaves: dict[tuple[str, ...], Any] = {}
    for key, value in node.items():
        if isinstance(value, dict):
            leaves |= _leaves(value, (*prefix, key))
        else:
            leaves[(*prefix, key)] = value
    return leaves


def _settings(model: type[BaseModel]) -> set[tuple[str, ...]]:
    """Return the path of every setting the model reads that is not a block of other settings or a secret."""
    blocks = {path[:-1] for path, _ in setting_paths(model)}
    return {path for path, secret in setting_paths(model) if not secret and path not in blocks}


def _defaults(model: type[BaseModel]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        value = field.get_default(call_default_factory=True)
        if isinstance(value, BaseModel):
            defaults[name] = value.model_dump(mode="json")
        elif isinstance(value, Enum):
            defaults[name] = value.value
        else:
            defaults[name] = value
    return defaults


def test_the_chart_writes_one_file_per_role(settings_files: dict[str, dict[str, Any]]):
    """Each backend role has its own settings file."""
    assert set(settings_files) == set(ROLES)


@pytest.mark.parametrize("role", ROLES)
def test_each_role_reads_the_file_the_chart_writes_for_it(
    role: str, settings_files: dict[str, dict[str, Any]], tmp_path: Path
):
    """No key in the file is unknown to the role, so the role starts with it."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump(settings_files[role]))

    load_role_settings(ROLES[role], config_file=config_file)


@pytest.mark.parametrize("role", ROLES)
def test_every_setting_a_role_reads_has_a_place_in_its_file(role: str, settings_files: dict[str, dict[str, Any]]):
    """A setting the backend gains needs a value in the chart, or it would only ever take its default."""
    missing = _settings(ROLES[role]) - NOT_IN_THE_FILE - set(_leaves(settings_files[role]))

    assert missing == set()


@pytest.mark.parametrize("role", ROLES)
def test_the_chart_s_generic_values_are_the_backend_s_defaults(role: str, settings_files: dict[str, dict[str, Any]]):
    """Where the chart does not point at an environment, it holds the same value the backend would use alone."""
    defaults = _leaves(_defaults(ROLES[role]))
    written = _leaves(settings_files[role])

    differing = {
        path: (value, defaults[path])
        for path, value in written.items()
        if path not in SET_BY_THE_ENVIRONMENT_OR_THE_CHART and value != defaults[path]
    }

    assert differing == {}


def test_the_exclusions_name_settings_that_exist():
    """An exclusion left behind by a renamed setting would hide nothing and should go."""
    known = set().union(*(_settings(model) for model in ROLES.values()))

    assert (NOT_IN_THE_FILE | SET_BY_THE_ENVIRONMENT_OR_THE_CHART) - known == set()
