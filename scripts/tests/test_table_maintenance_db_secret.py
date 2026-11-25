"""Test the Secret the table maintenance database wave leaves behind: it holds the login, user and password both."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WAVE = REPO_ROOT / "platform" / "20-table-maintenance-db"
USER = "table_maintenance"

pytestmark = pytest.mark.skipif(shutil.which("openssl") is None, reason="bootstrap.sh generates the password")


def _bootstrap(tmp_path: Path, *, secret: dict[str, str] | None) -> list[str]:
    """Run bootstrap.sh against a kubectl that knows only the given Secret data (None: no Secret yet).

    Returns every kubectl call, one argument list per line.
    """
    calls = tmp_path / "calls"
    stub = tmp_path / "kubectl"
    name_answer = "secret/table-maintenance-db" if secret is not None else ""
    username = base64.b64encode((secret or {}).get("username", "").encode()).decode() if secret else ""
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{calls}"\n'
        'if [[ "$1 $2" == "get secret" && "$*" == *"-o name"* ]]; then '
        f'echo "{name_answer}"; fi\n'
        'if [[ "$1 $2" == "get secret" && "$*" == *"data.username"* ]]; then '
        f'printf "%s" "{username}"; fi\n'
        "cat >/dev/null 2>&1 || true\n"
    )
    stub.chmod(0o755)
    subprocess.run(
        ["bash", str(WAVE / "bootstrap.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "KUBE_CONTEXT": "none"},
        check=True,
        timeout=60,
    )
    return calls.read_text().splitlines()


def test_a_new_cluster_gets_a_secret_with_the_user_and_the_password(tmp_path: Path):
    """The first run creates the Secret with both keys the chart reads."""
    (create,) = [call for call in _bootstrap(tmp_path, secret=None) if call.startswith("create secret")]
    assert f"--from-literal=username={USER}" in create
    assert "--from-file=password=/dev/stdin" in create


def test_an_older_secret_without_the_user_gets_it_added(tmp_path: Path):
    """A cluster built before the user moved into the Secret keeps its password and gains the user."""
    calls = _bootstrap(tmp_path, secret={"password": "kept"})
    assert not [call for call in calls if call.startswith("create secret")]
    (patch,) = [call for call in calls if call.startswith("patch secret table-maintenance-db")]
    assert f'"username":"{USER}"' in patch
    assert "password" not in patch


def test_a_secret_that_has_the_user_is_left_alone(tmp_path: Path):
    """A rerun changes nothing in a complete Secret."""
    calls = _bootstrap(tmp_path, secret={"username": USER, "password": "kept"})
    assert not [call for call in calls if call.startswith(("create secret", "patch secret"))]


def test_the_database_takes_its_user_from_the_secret():
    """PostgreSQL creates the same user the chart logs in as, both read from one Secret key."""
    deployment = yaml.safe_load((WAVE / "table-maintenance-db-deployment.yaml").read_text())
    (container,) = deployment["spec"]["template"]["spec"]["containers"]
    env = {entry["name"]: entry for entry in container["env"]}
    assert env["POSTGRES_USER"]["valueFrom"]["secretKeyRef"] == {"name": "table-maintenance-db", "key": "username"}
