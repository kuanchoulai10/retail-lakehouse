#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uninstalling Thanos (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/manifests/" --context "${KUBE_CONTEXT}"

echo "==> Done."
