"""Test the wave-25 environment files: the minikube environment, the e2e overlay and how bootstrap.sh picks them."""

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
MINIKUBE = WAVE / "values" / "minikube.yaml"
E2E = WAVE / "values" / "e2e.yaml"
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
    command += ["--values", str(MINIKUBE)]
    for image in ("backend.image", "maintenance.jobs.image", "frontend.image"):
        command += ["--set-string", f"{image}.tag=test"]
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


def test_the_minikube_environment_writes_every_role_s_settings_without_a_profile_label():
    """The minikube environment alone renders a settings file per role, and no role carries a profile label."""
    config_maps = _config_maps()
    assert set(config_maps) == set(ROLES)
    for doc in config_maps.values():
        assert not any(key.startswith("retail-lakehouse.io/") for key in doc["metadata"]["labels"])


def test_the_e2e_overlay_shortens_only_its_waits():
    """The overlay changes the four waits a maintenance scenario sits through, for the API and the worker alike."""
    default = _settings()
    e2e = _settings("--values", str(E2E))
    for role in ("api", "worker"):
        assert {key: e2e[role]["maintenance"][key] for key in E2E_MAINTENANCE} == E2E_MAINTENANCE
        assert all(default[role]["maintenance"][key] > bound for key, bound in E2E_MAINTENANCE.items())
        for key in E2E_MAINTENANCE:
            e2e[role]["maintenance"][key] = default[role]["maintenance"][key]
    assert e2e == default


def test_the_e2e_overlay_names_no_environment():
    """The overlay only shortens waits; where the services are comes from the environment file alone."""
    assert set(yaml.safe_load(E2E.read_text())) == {"maintenance"}


def test_changing_one_role_s_config_restarts_only_that_role():
    """Each Deployment's checksum covers its own settings file only."""
    before = _checksums()
    after = _checksums("--set", "backend.worker.logLevel=DEBUG")
    assert after["table-maintenance-worker"] != before["table-maintenance-worker"]
    assert after["table-maintenance-api"] == before["table-maintenance-api"]
    assert after["table-maintenance-event-consumer"] == before["table-maintenance-event-consumer"]


def test_a_shared_setting_restarts_every_role_that_reads_it():
    """A change to a shared block the API and the worker both read restarts both, and not the event consumer."""
    before = _checksums()
    after = _checksums("--set", "maintenance.jobs.limits.maxAttempts=5")
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
    assert "--set " not in script
    for image in ("backend.image", "maintenance.jobs.image", "frontend.image"):
        assert f'--set-string {image}.tag="' in script


def test_bootstrap_sets_nothing_but_the_image_tags():
    """Every other value comes from the environment file, so the deploy and the file cannot disagree."""
    script = (WAVE / "bootstrap.sh").read_text()
    assert sorted(re.findall(r"--set-string (\S+)=", script)) == [
        "backend.image.tag",
        "frontend.image.tag",
        "maintenance.jobs.image.tag",
    ]


def test_bootstrap_deploys_the_minikube_environment_then_the_profile_overlay():
    """The environment file comes first, so the e2e overlay can change what it sets."""
    script = (WAVE / "bootstrap.sh").read_text()
    environment = script.index('--values "${SCRIPT_DIR}/values/minikube.yaml"')
    overlay = script.index('${PROFILE_VALUES[@]+"${PROFILE_VALUES[@]}"}')
    assert environment < overlay
    assert 'PROFILE_VALUES=(--values "${SCRIPT_DIR}/values/e2e.yaml")' in script


def test_the_chart_names_no_table_or_seed():
    """The services wait for the schema through the backend, so no table name or seed id lives in the chart."""
    rendered = yaml.safe_dump_all(_render())
    assert not re.search(r"table_maintenance_policies|table_discovery_policies|dp-0000|psql", rendered)


def test_bootstrap_gives_the_s3_secret_the_region_of_the_environment_file():
    """The S3 Secret's region is read from the environment file the settings come from, so they cannot differ."""
    script = (WAVE / "bootstrap.sh").read_text()
    assert 'AWS_REGION: "%s"' in script
    assert 'S3_REGION="$(yq \'.external.objectStorage.s3.region\' "${SCRIPT_DIR}/values/minikube.yaml")"' in script
    assert 'S3_REGION="dummy-region"' not in script
