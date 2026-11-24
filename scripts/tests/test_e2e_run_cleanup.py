"""Test what the wave-25 e2e runner removes when it exits: its pod, and the queue holders its run may have left."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E = REPO_ROOT / "platform" / "25-lakehouse-control-plane" / "e2e"
HOLDER_SELECTOR = "app.kubernetes.io/name=table-maintenance-e2e,app.kubernetes.io/component=queue-holder"

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("git", "jq", "envsubst", "openssl")),
    reason="run.sh needs git, jq, envsubst and openssl",
)


def _run(tmp_path: Path, *, active_pods: list[dict] | None) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run a copy of run.sh in a throwaway repo whose kubectl answers the pod list and fails the pod's apply.

    ``active_pods`` None makes the pod list itself fail.
    """
    repo = tmp_path / "repo"
    wave = repo / "platform" / "25-lakehouse-control-plane"
    (wave / "e2e").mkdir(parents=True)
    (repo / "scripts" / "utils").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "scripts" / "utils" / "log.sh", repo / "scripts" / "utils" / "log.sh")
    for name in ("run.sh", "rbac.yaml", "pod.yaml"):
        shutil.copy(E2E / name, wave / "e2e" / name)
    (wave / "build.sh").write_text("#!/usr/bin/env bash\necho E2E_TAG=test\n")
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    pods = tmp_path / "pods.json"
    if active_pods is not None:
        pods.write_text(json.dumps({"items": active_pods}))
    kubectl = bin_dir / "kubectl"
    kubectl.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{calls}"\n'
        f'if [[ "$1 $2" == "get pods" ]]; then cat "{pods}"; exit; fi\n'
        'if [[ "$*" == "apply -f - "* ]]; then cat >/dev/null; exit 1; fi\n'
        "exit 0\n"
    )
    kubectl.chmod(0o755)
    finished = subprocess.run(
        ["bash", str(wave / "e2e" / "run.sh"), "full"],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "KUBE_CONTEXT": "test"},
        check=False,
        timeout=60,
    )
    return finished, calls.read_text().splitlines() if calls.exists() else []


def test_an_exit_after_the_run_started_deletes_the_queue_holders(tmp_path: Path):
    """A holder outlives a pod killed outright, and holds the normal queue until it is deleted."""
    finished, calls = _run(tmp_path, active_pods=[])
    assert finished.returncode != 0
    assert (
        f"delete podgroups --namespace lakehouse-maintenance-operations --context test "
        f"--selector {HOLDER_SELECTOR} --ignore-not-found --wait=false"
    ) in calls, calls


def test_an_exit_because_another_run_is_going_leaves_its_holders(tmp_path: Path):
    """The other run's scenario may be holding the queue on purpose."""
    running = {"metadata": {"name": "table-maintenance-e2e-other"}, "status": {"phase": "Running"}}
    finished, calls = _run(tmp_path, active_pods=[running])
    assert finished.returncode == 1
    assert "another e2e run is still going" in finished.stderr
    assert not [call for call in calls if "podgroups" in call], calls


def test_an_exit_before_the_run_knows_it_is_alone_leaves_every_holder(tmp_path: Path):
    """When the check for another run fails, a holder on the cluster may still be that run's."""
    finished, calls = _run(tmp_path, active_pods=None)
    assert finished.returncode != 0
    assert calls and calls[0].startswith("get pods"), calls
    assert not [call for call in calls if "podgroups" in call], calls
