"""Test that the API answers on the paths the wave-25 chart probes it at."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from bootstrap.container import create_api_app

CHART = Path(__file__).resolve().parents[6] / "platform" / "25-lakehouse-control-plane" / "chart"

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm renders the chart")


@pytest.fixture(scope="module")
def rendered() -> list[dict[str, Any]]:
    """Return the API Deployment, its settings and the connection test as the chart renders them."""
    output = subprocess.run(
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
    return [doc for doc in yaml.safe_load_all(output) if doc]


def _named(rendered: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    return next(doc for doc in rendered if doc["kind"] == kind and doc["metadata"]["name"] == name)


def test_the_api_answers_its_readiness_and_liveness_probes(rendered: list[dict[str, Any]]):
    """A probe on a path the API does not serve would keep it unready, or restart it forever."""
    container = _named(rendered, "Deployment", "table-maintenance-api")["spec"]["template"]["spec"]["containers"][0]
    settings = yaml.safe_load(_named(rendered, "ConfigMap", "table-maintenance-api-config")["data"]["config.yaml"])
    client = TestClient(create_api_app(root_path=settings["http"]["root_path"]))

    for probe in ("readinessProbe", "livenessProbe"):
        assert client.get(container[probe]["httpGet"]["path"]).status_code == 200, probe
