"""Check that the Kubernetes objects we author follow the label standard.

Every object carries the recommended labels app.kubernetes.io/{name,instance,part-of,managed-by}
and no unprefixed label key. Workload pod templates carry the same app.kubernetes.io/* values as
their object. Deployment / StatefulSet / DaemonSet / Service selectors use only
app.kubernetes.io/{name,instance,component}, always name and instance, and match the pod template.

Scope: every platform/**/*.yaml we write (third-party Helm values, vendored charts, CRD bundles,
on-hold waves and patches of third-party objects are excluded) plus the rendered wave-25 chart.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

PREFIX = "app.kubernetes.io/"
REQUIRED = tuple(PREFIX + key for key in ("name", "instance", "part-of", "managed-by"))
SELECTOR_KEYS = tuple(PREFIX + key for key in ("name", "instance", "component"))
SELECTOR_REQUIRED = SELECTOR_KEYS[:2]
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Job"}
SELECTED_WORKLOAD_KINDS = WORKLOAD_KINDS - {"Job"}

EXCLUDED = re.compile(
    r"^platform/("
    r"(30-thanos|24-e2e-validation|00-argocd|01-argocd-health-checks|02-argocd-apps)/"
    r"|11-gateway-api-crds/manifests/"
    r"|10-kube-prometheus/dev-overrides\.yaml$"
    r"|25-lakehouse-control-plane/chart/"
    r"|[^/]+/charts/"
    r"|.*/values[^/]*\.yaml$"
    r"|.*/Chart\.yaml$"
    r")"
)
CHART = "platform/25-lakehouse-control-plane/chart"


def _label_violations(labels: dict, where: str) -> list[str]:
    violations = [f"{where} is missing {key}" for key in REQUIRED if key not in labels]
    violations += [f"{where} uses unprefixed key '{key}'" for key in labels if "/" not in key]
    return violations


def _selector_violations(selector: dict, pod_labels: dict | None, where: str) -> list[str]:
    violations = []
    extra = sorted(key for key in selector if key not in SELECTOR_KEYS)
    if extra:
        violations.append(f"{where} selector may only use {', '.join(SELECTOR_KEYS)} (found {', '.join(extra)})")
    violations += [f"{where} selector is missing {key}" for key in SELECTOR_REQUIRED if key not in selector]
    if pod_labels is not None:
        violations += [
            f"{where} selector {key}={value} does not match the pod template"
            for key, value in selector.items()
            if pod_labels.get(key) != value
        ]
    return violations


def check_document(doc: dict, source: str) -> list[str]:
    """Return the label-standard violations of one Kubernetes object."""
    if not isinstance(doc, dict) or "kind" not in doc:
        return []
    kind = doc["kind"]
    metadata = doc.get("metadata") or {}
    where = f"{source}: {kind}/{metadata.get('name', '?')}"
    labels = metadata.get("labels") or {}
    violations = _label_violations(labels, f"{where} metadata.labels")

    spec = doc.get("spec") or {}
    pod_labels = None
    if kind in WORKLOAD_KINDS:
        pod_labels = ((spec.get("template") or {}).get("metadata") or {}).get("labels") or {}
        violations += _label_violations(pod_labels, f"{where} pod template labels")
        violations += [
            f"{where} pod template label {key} is '{pod_labels[key]}', metadata has '{value}'"
            for key, value in labels.items()
            if key.startswith(PREFIX) and key in pod_labels and pod_labels[key] != value
        ]

    if kind in SELECTED_WORKLOAD_KINDS:
        selector = (spec.get("selector") or {}).get("matchLabels") or {}
        violations += _selector_violations(selector, pod_labels, where)
    elif kind == "Service" and spec.get("selector"):
        violations += _selector_violations(spec["selector"], None, where)
    return violations


def manifest_files(root: Path) -> list[Path]:
    """Return the platform manifests we author, excluding third-party and on-hold files."""
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "platform"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    return sorted(root / path for path in tracked if path.endswith(".yaml") and not EXCLUDED.match(path))


def rendered_chart(root: Path) -> str:
    """Render the wave-25 chart with placeholder image tags."""
    return subprocess.run(
        [
            "helm",
            "template",
            "table-maintenance",
            str(root / CHART),
            "--namespace",
            "lakehouse-control-plane",
            "--set",
            "image.backend.tag=check",
            "--set",
            "image.spark.tag=check",
            "--set",
            "image.console.tag=check",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main() -> int:
    """Check every authored manifest and the rendered chart; return the exit code."""
    root = Path(__file__).resolve().parents[1]
    sources = [(str(path.relative_to(root)), path.read_text()) for path in manifest_files(root)]
    sources.append((f"{CHART} (rendered)", rendered_chart(root)))
    violations = [
        violation
        for source, text in sources
        for doc in yaml.safe_load_all(text)
        for violation in check_document(doc, source)
    ]
    for violation in violations:
        print(violation)
    if violations:
        print(f"{len(violations)} label violation(s); see CLAUDE.md 'Kubernetes labels'", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
