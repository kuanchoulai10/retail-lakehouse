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
NEEDED_TOOLS = ("bash", "sh", "jq", "tr", "cat")


def _run(path: str, env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {"PATH": path, "HOME": os.environ.get("HOME", "")}
    env.update(env_extra)
    return subprocess.run(
        [str(Path(path) / "bash"), "-c", f"source {ORIGIN_SH}; origin::public"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    """Directory of symlinks to only the tools the helper needs, used as the whole PATH."""
    directory = tmp_path / "bin"
    directory.mkdir()
    for tool in NEEDED_TOOLS:
        found = shutil.which(tool)
        assert found, f"{tool} is required to run this test"
        (directory / tool).symlink_to(found)
    return directory


@pytest.fixture
def fake_tailscale(bin_dir: Path):
    """Add a fake tailscale that reports the given DNS name; return the PATH."""

    def make(dns_name: str) -> str:
        script = bin_dir / "tailscale"
        payload = json.dumps({"Self": {"DNSName": dns_name}})
        script.write_text(f"#!/bin/sh\ncat <<'JSON'\n{payload}\nJSON\n")
        script.chmod(0o755)
        return str(bin_dir)

    return make


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


def test_fails_without_tailscale(bin_dir: Path) -> None:
    """Without tailscale and an override the helper fails."""
    assert shutil.which("tailscale", path=str(bin_dir)) is None
    result = _run(str(bin_dir), {})
    assert result.returncode == 1
    assert "public origin unknown" in result.stderr


def test_fails_on_empty_dns_name(fake_tailscale) -> None:
    """An empty DNS name fails."""
    path = fake_tailscale("")
    result = _run(path, {})
    assert result.returncode == 1
    assert "public origin unknown" in result.stderr
