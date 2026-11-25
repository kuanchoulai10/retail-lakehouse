"""Test the wave-25 settings profiles: the default values, the e2e overlay and how bootstrap.sh picks one."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WAVE = REPO_ROOT / "platform" / "25-lakehouse-control-plane"
CHART = WAVE / "chart"
PROFILE_LABEL = "retail-lakehouse.io/settings-profile"
E2E_MAINTENANCE = {
    "compaction_quiet_seconds": 60,
    "compaction_max_quiet_wait_seconds": 180,
    "rewrite_data_files_cooldown_seconds": 60,
    "queue_wait_limit_seconds": 900,
}
ROLES = ("api", "worker", "event-consumer", "migrate")

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm renders the chart")


def _render(*arguments: str) -> list[dict]:
    command = ["helm", "template", "table-maintenance", str(CHART), "--namespace", "lakehouse-control-plane"]
    for image in ("backend", "spark", "console"):
        command += ["--set", f"image.{image}.tag=test"]
    command += arguments
    rendered = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    return [doc for doc in yaml.safe_load_all(rendered) if doc]


def _config_maps(*arguments: str) -> dict[str, dict]:
    """Return each role's config map by role, as the chart rendered it."""
    return {
        doc["metadata"]["name"].removeprefix("table-maintenance-").removesuffix("-config"): doc
        for doc in _render(*arguments)
        if doc["kind"] == "ConfigMap" and doc["metadata"]["name"].endswith("-config")
    }


def _settings(*arguments: str) -> dict[str, dict]:
    """Return each role's settings file, parsed."""
    return {role: yaml.safe_load(doc["data"]["config.yaml"]) for role, doc in _config_maps(*arguments).items()}


def _checksums(*arguments: str) -> dict[str, str]:
    return {
        doc["metadata"]["name"]: doc["spec"]["template"]["metadata"]["annotations"]["checksum/config"]
        for doc in _render(*arguments)
        if doc["kind"] == "Deployment" and doc["metadata"]["name"] != "table-maintenance-console"
    }


def test_the_default_values_render_the_default_profile():
    """Without the overlay every role runs Pydantic's defaults: no maintenance setting is written, and it says so."""
    config_maps = _config_maps()
    assert set(config_maps) == set(ROLES)
    for doc in config_maps.values():
        assert doc["metadata"]["labels"][PROFILE_LABEL] == "default"
        assert "maintenance" not in yaml.safe_load(doc["data"]["config.yaml"])


def test_the_e2e_overlay_shortens_only_its_waits():
    """The overlay changes the four waits a maintenance scenario sits through, for the API and the worker alike."""
    default = _settings()
    e2e = _settings("-f", str(CHART / "values-e2e.yaml"))
    for doc in _config_maps("-f", str(CHART / "values-e2e.yaml")).values():
        assert doc["metadata"]["labels"][PROFILE_LABEL] == "e2e"
    for role in ("api", "worker"):
        assert e2e[role].pop("maintenance") == E2E_MAINTENANCE
    assert e2e == default


def test_changing_one_role_s_config_restarts_only_that_role():
    """Each Deployment's checksum covers its own settings file only."""
    before = _checksums()
    after = _checksums("--set", "worker.config.log_level=DEBUG")
    assert after["table-maintenance-worker"] != before["table-maintenance-worker"]
    assert after["table-maintenance-api"] == before["table-maintenance-api"]
    assert after["table-maintenance-event-consumer"] == before["table-maintenance-event-consumer"]


def test_a_shared_setting_restarts_every_role_that_reads_it():
    """A change to a shared block the API and the worker both read restarts both, and not the event consumer."""
    before = _checksums()
    after = _checksums("--set", "config.maintenance.max_attempts=5")
    assert after["table-maintenance-worker"] != before["table-maintenance-worker"]
    assert after["table-maintenance-api"] != before["table-maintenance-api"]
    assert after["table-maintenance-event-consumer"] == before["table-maintenance-event-consumer"]


def test_bootstrap_refuses_an_unknown_profile_before_it_touches_the_cluster(tmp_path: Path):
    """A typo in the profile stops the deploy at once; no kubectl or helm runs."""
    calls = tmp_path / "calls"
    for tool in ("kubectl", "helm"):
        stub = tmp_path / tool
        stub.write_text(f'#!/usr/bin/env bash\necho {tool} >> "{calls}"\n')
        stub.chmod(0o755)
    finished = subprocess.run(
        ["bash", str(WAVE / "bootstrap.sh")],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "KUBE_CONTEXT": "none",
            "SETTINGS_PROFILE": "bogus",
        },
        check=False,
        timeout=30,
    )
    assert finished.returncode != 0
    assert "SETTINGS_PROFILE must be default or e2e" in finished.stderr
    assert not calls.exists()


def test_bootstrap_passes_image_tags_as_strings():
    """A short SHA of digits stays a string, so the schema's string tag accepts it."""
    script = (WAVE / "bootstrap.sh").read_text()
    assert "--set image." not in script
    for image in ("backend", "spark", "console"):
        assert f'--set-string image.{image}.tag="' in script


def test_the_chart_names_no_table_or_seed():
    """The services wait for the schema through the backend, so no table name or seed id lives in the chart."""
    for migrate_enabled in ("true", "false"):
        rendered = yaml.safe_dump_all(_render("--set", f"migrate.enabled={migrate_enabled}"))
        assert not re.search(r"table_maintenance_policies|table_discovery_policies|dp-0000|psql", rendered)


def test_bootstrap_gives_the_settings_the_region_it_gives_the_s3_secret():
    """One region reaches both the S3 Secret and the catalog settings, so they cannot differ."""
    script = (WAVE / "bootstrap.sh").read_text()
    assert 'AWS_REGION: "%s"' in script
    assert '--set-string config.catalog.s3_region="${S3_REGION}"' in script
