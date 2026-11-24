"""Test the wave-25 settings profiles: the default values, the e2e overlay and how bootstrap.sh picks one."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WAVE = REPO_ROOT / "platform" / "25-lakehouse-control-plane"
CHART = WAVE / "chart"
PROFILE_LABEL = "retail-lakehouse.io/settings-profile"
E2E_VALUES = {
    "GLAC_MAINTENANCE_COMPACTION_QUIET_SECONDS": "60",
    "GLAC_MAINTENANCE_COMPACTION_MAX_QUIET_WAIT_SECONDS": "180",
    "GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS": "60",
    "GLAC_MAINTENANCE_QUEUE_WAIT_LIMIT_SECONDS": "900",
}

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm renders the chart")


def _config(*values_files: Path) -> dict:
    command = ["helm", "template", "table-maintenance", str(CHART), "--namespace", "lakehouse-control-plane"]
    for image in ("backend", "spark", "console"):
        command += ["--set", f"image.{image}.tag=test"]
    for values in values_files:
        command += ["-f", str(values)]
    rendered = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    [config] = [
        doc
        for doc in yaml.safe_load_all(rendered)
        if doc and doc["kind"] == "ConfigMap" and doc["metadata"]["name"] == "table-maintenance-config"
    ]
    return config


def test_the_default_values_render_the_default_profile():
    """Without the overlay the platform runs the chart's defaults and says so."""
    config = _config()
    assert config["metadata"]["labels"][PROFILE_LABEL] == "default"
    assert config["data"]["GLAC_MAINTENANCE_COMPACTION_QUIET_SECONDS"] == "120"
    assert config["data"]["GLAC_MAINTENANCE_REWRITE_DATA_FILES_COOLDOWN_SECONDS"] == "3600"


def test_the_e2e_overlay_shortens_only_its_waits():
    """The overlay changes the four waits a maintenance scenario sits through and nothing else."""
    default = _config()["data"]
    e2e = _config(CHART / "values-e2e.yaml")
    assert e2e["metadata"]["labels"][PROFILE_LABEL] == "e2e"
    assert {key: e2e["data"][key] for key in E2E_VALUES} == E2E_VALUES
    assert {k: v for k, v in e2e["data"].items() if k not in E2E_VALUES} == {
        k: v for k, v in default.items() if k not in E2E_VALUES
    }


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
