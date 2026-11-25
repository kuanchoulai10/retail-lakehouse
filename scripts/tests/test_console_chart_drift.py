"""Test that the wave-25 chart serves the console where the console image and its build expect."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / "platform" / "25-lakehouse-control-plane" / "chart"
FRONTEND = ROOT / "src" / "data-platform" / "frontend"

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm renders the chart")


@pytest.fixture(scope="module")
def console() -> dict[str, dict]:
    """Return the console's objects, by kind, as the chart renders them for a whole environment."""
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
            "--show-only",
            "templates/console.yaml",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {doc["kind"]: doc for doc in yaml.safe_load_all(rendered) if doc}


def _base_path() -> str:
    match = re.search(r'^\s*base:\s*"([^"]+)"', (FRONTEND / "vite.config.ts").read_text(), re.MULTILINE)
    assert match, "vite.config.ts names no base"
    return match.group(1)


def test_the_image_listens_on_the_port_the_chart_gives_it():
    """The image's nginx listens on CONSOLE_PORT, which defaults to the chart's default port and is EXPOSEd."""
    default_port = yaml.safe_load((CHART / "values.yaml").read_text())["frontend"]["console"]["port"]
    dockerfile = (FRONTEND / "Dockerfile").read_text()

    assert re.search(r"^\s*listen \$\{CONSOLE_PORT\};$", (FRONTEND / "console.conf.template").read_text(), re.MULTILINE)
    assert re.search(rf"^\s*CONSOLE_PORT={default_port}\b", dockerfile, re.MULTILINE)
    assert re.search(rf"^EXPOSE {default_port}$", dockerfile, re.MULTILINE)


def test_the_route_and_the_probes_use_the_path_the_console_is_built_for(console: dict[str, dict]):
    """The console is built under one base path; the gateway sends that prefix to it and the probes ask for it."""
    base = _base_path()
    container = console["Deployment"]["spec"]["template"]["spec"]["containers"][0]
    [match] = console["HTTPRoute"]["spec"]["rules"][0]["matches"]

    assert match["path"]["value"] == base.rstrip("/")
    assert container["readinessProbe"]["httpGet"]["path"] == base
    assert container["livenessProbe"]["httpGet"]["path"] == base
    assert f"location {base} {{" in (FRONTEND / "console.conf.template").read_text()
