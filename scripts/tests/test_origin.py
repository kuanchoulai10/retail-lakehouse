"""Test the public origin helper."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ORIGIN_SH = REPO_ROOT / "scripts" / "utils" / "origin.sh"


def _run(path: str, env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {"PATH": path, "HOME": os.environ.get("HOME", "")}
    env.update(env_extra)
    return subprocess.run(
        [shutil.which("bash") or "bash", "-c", f"source {ORIGIN_SH}; origin::public"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture
def fake_tailscale(tmp_path: Path):
    """Build a PATH holding a fake tailscale that reports the given DNS name."""

    def make(dns_name: str) -> str:
        bin_dir = tmp_path / "fakebin"
        bin_dir.mkdir(exist_ok=True)
        script = bin_dir / "tailscale"
        payload = json.dumps({"Self": {"DNSName": dns_name}})
        script.write_text(f"#!/bin/sh\ncat <<'JSON'\n{payload}\nJSON\n")
        script.chmod(0o755)
        return f"{bin_dir}:{_base_path()}"

    return make


def _base_path() -> str:
    dirs = {str(Path(shutil.which(tool) or "").parent) for tool in ("bash", "jq")}
    return ":".join(sorted(d for d in dirs if d and d != "."))


def test_override_wins(fake_tailscale) -> None:
    """PUBLIC_ORIGIN wins over tailscale and loses its trailing slash."""
    path = fake_tailscale("Other.ts.net.")
    result = _run(path, {"PUBLIC_ORIGIN": "https://x.example:8591/"})
    assert result.returncode == 0
    assert result.stdout.strip() == "https://x.example:8591"


def test_detects_tailscale_name(fake_tailscale) -> None:
    """The tailscale DNS name is lowercased and stripped of its trailing dot."""
    path = fake_tailscale("Host.Tail1.ts.net.")
    result = _run(path, {})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "https://host.tail1.ts.net:8591"


def test_fails_without_tailscale(tmp_path: Path) -> None:
    """Without tailscale and an override the helper fails."""
    result = _run(_base_path(), {})
    assert not (tmp_path / "tailscale").exists()
    assert result.returncode == 1
    assert "public origin unknown" in result.stderr


def test_fails_on_empty_dns_name(fake_tailscale) -> None:
    """An empty DNS name fails."""
    path = fake_tailscale("")
    result = _run(path, {})
    assert result.returncode == 1
    assert "public origin unknown" in result.stderr
