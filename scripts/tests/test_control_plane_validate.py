"""Test what the wave-25 validate.sh asserts about table discovery, against a stubbed kubectl, helm and curl."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WAVE = REPO_ROOT / "platform" / "25-lakehouse-control-plane"

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("jq", "yq")),
    reason="validate.sh needs jq and yq",
)

WORKER_CONFIG = """spark:
  volcano:
    queue: table-maintenance
    urgent_queue: table-maintenance-urgent
    priority_class_prefix: table-maintenance
"""

CONSUMER_GROUP = (
    "GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID HOST CLIENT-ID\n"
    "table-maintenance-event-consumer polaris-catalog-events 0 5 5 0 consumer-1 /10.0.0.1 client-1\n"
)

KUBECTL = r"""#!/usr/bin/env bash
fixtures="__FIXTURES__"
args="$*"
last="${!#}"
case "${args}" in
  "get namespace "*dataplane-mode*) echo ambient ;;
  "get namespace "*gateway-routes*) echo allowed ;;
  "wait "* | "rollout status "*) ;;
  "get configmap table-maintenance-worker-config "*) cat "${fixtures}/worker-config.yaml" ;;
  "get queue.scheduling.volcano.sh/"*) echo 5017Mi ;;
  "get priorityclass/"*) echo Never ;;
  "get secret keycloak-clients "*) ;;
  "port-forward "*) echo "Forwarding from 127.0.0.1:12345 -> 80"; exec /bin/sleep 30 ;;
  "exec deployment/table-maintenance-api "*HTTPError*)
    route="$(grep -oE "localhost:8000[^']*" <<<"${args}" | head -n 1)"
    route="${route#localhost:8000}"
    jq -r --arg path "${route}" '.[$path].status // 404' "${fixtures}/api.json" ;;
  "exec deployment/table-maintenance-api "*)
    status="$(jq -r --arg path "${last}" '.[$path].status // 404' "${fixtures}/api.json")"
    if [[ "${status}" != "200" ]]; then
      echo "urllib.error.HTTPError: HTTP Error ${status}" >&2
      exit 1
    fi
    if [[ "${args}" == *"r.status"* ]]; then
      echo "${last} 200"
    else
      jq -c --arg path "${last}" '.[$path].body' "${fixtures}/api.json"
    fi ;;
  "exec deployment/temporal-admintools "*"schedule list"*) cat "${fixtures}/schedules.json" ;;
  "exec deployment/temporal-admintools "*"schedule describe"*)
    schedule="${args##*--schedule-id }"
    schedule="${schedule%% *}"
    described="$(jq -c --arg id "${schedule}" '.[$id] // empty' "${fixtures}/described.json")"
    if [[ -z "${described}" ]]; then
      echo "Error: unable to describe schedule: schedule not found" >&2
      exit 1
    fi
    echo "${described}" ;;
  "exec deployment/temporal-admintools "*"workflow describe"*)
    echo "Error: workflow not found for ID: table-maintenance-admission" >&2
    exit 1 ;;
  "exec kafka-cluster-dual-role-0 "*) cat "${fixtures}/consumer-group.txt" ;;
  *) echo "unexpected kubectl call: ${args}" >&2; exit 2 ;;
esac
"""

HELM = r"""#!/usr/bin/env bash
case "$1" in
  status) echo '{"version": 3}' ;;
  test) ;;
  *) echo "unexpected helm call: $*" >&2; exit 2 ;;
esac
"""

CURL = r"""#!/usr/bin/env bash
url="${!#}"
path="/${url#http://127.0.0.1:12345/}"
case "${path}" in
  /console | /console/ | /console/catalogs) echo '<div id="root"></div>' ;;
  /console/api/v1/tables | /api/v1/tables) echo '[]' ;;
  /api/openapi.json) echo '{"servers": [{"url": "/api"}]}' ;;
  /api/docs) echo "url: '/api/openapi.json'" ;;
  *) echo "unexpected curl call: $*" >&2; exit 22 ;;
esac
"""


def _api() -> dict[str, dict]:
    """The API answers of a healthy control plane, keyed by path."""
    return {
        "/healthz": {"status": 200, "body": {"status": "ok"}},
        "/v1/discovery-policies": {"status": 200, "body": []},
        "/v1/scanned-catalogs": {"status": 200, "body": {"catalogs": [{"catalog": "lake"}]}},
        "/v1/maintenance-policies/default": {"status": 200, "body": {"name": "default", "is_default": True}},
        "/v1/tables": {"status": 200, "body": []},
        "/v1/catalogs": {"status": 200, "body": []},
    }


def _schedule(schedule_id: str, *, paused: bool = False) -> dict:
    """A schedule list entry as the Temporal CLI prints it, which leaves ``paused`` out while it is false."""
    info: dict = {"workflowType": {"name": "TableDiscoveryRoundWorkflow"}}
    if paused:
        info["paused"] = True
    return {"scheduleId": schedule_id, "info": info}


def _described(*, paused: bool = False) -> dict:
    """A schedule description as the Temporal CLI prints it."""
    state: dict = {"paused": True} if paused else {}
    return {"schedule": {"spec": {"interval": [{"interval": "600s"}]}, "state": state}}


def _run(
    tmp_path: Path,
    *,
    api: dict[str, dict] | None = None,
    schedules: list[dict] | None = None,
    described: dict[str, dict] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a copy of validate.sh whose cluster answers the given API, schedule list and schedule descriptions."""
    repo = tmp_path / "repo"
    wave = repo / "platform" / "25-lakehouse-control-plane"
    wave.mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "scripts" / "utils", repo / "scripts" / "utils")
    shutil.copy(WAVE / "validate.sh", wave / "validate.sh")
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "api.json").write_text(json.dumps(_api() if api is None else api))
    (fixtures / "schedules.json").write_text(
        json.dumps([_schedule("table-discovery")] if schedules is None else schedules)
    )
    (fixtures / "described.json").write_text(
        json.dumps({"table-discovery": _described()} if described is None else described)
    )
    (fixtures / "worker-config.yaml").write_text(WORKER_CONFIG)
    (fixtures / "consumer-group.txt").write_text(CONSUMER_GROUP)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (
        ("kubectl", KUBECTL.replace("__FIXTURES__", str(fixtures))),
        ("helm", HELM),
        ("curl", CURL),
        ("sleep", "#!/usr/bin/env bash\nexit 0\n"),
    ):
        stub = bin_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    return subprocess.run(
        ["bash", str(wave / "validate.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "KUBE_CONTEXT": "test", "NO_COLOR": "1"},
        check=False,
        timeout=120,
    )


def test_a_healthy_control_plane_passes(tmp_path: Path):
    """One unpaused discovery schedule and no default discovery policy is the healthy state."""
    finished = _run(tmp_path)
    assert finished.returncode == 0, finished.stderr


def test_a_default_discovery_policy_fails(tmp_path: Path):
    """There is no default discovery policy any more, so the route by that name answers 404."""
    api = {**_api(), "/v1/discovery-policies/default": {"status": 200, "body": {"name": "default"}}}
    finished = _run(tmp_path, api=api)
    assert finished.returncode != 0
    assert "/v1/discovery-policies/default returned 200, expected 404" in finished.stderr


def test_a_missing_discovery_schedule_fails(tmp_path: Path):
    """The worker ensures the one schedule at start, so its absence means the worker never did."""
    finished = _run(tmp_path, schedules=[], described={})
    assert finished.returncode != 0
    assert "expected exactly one schedule table-discovery" in finished.stderr


def test_a_paused_discovery_schedule_fails(tmp_path: Path):
    """A paused schedule fires no round, so no catalog is scanned."""
    finished = _run(
        tmp_path,
        schedules=[_schedule("table-discovery", paused=True)],
        described={"table-discovery": _described(paused=True)},
    )
    assert finished.returncode != 0
    assert "schedule table-discovery is paused" in finished.stderr


def test_a_leftover_per_catalog_schedule_fails(tmp_path: Path):
    """Catalog scans are started by the round now; a schedule per catalog is a leftover of the old design."""
    finished = _run(tmp_path, schedules=[_schedule("table-discovery"), _schedule("table-discovery:catalog=lake")])
    assert finished.returncode != 0
    assert "per-catalog discovery schedules remain: table-discovery:catalog=lake" in finished.stderr
