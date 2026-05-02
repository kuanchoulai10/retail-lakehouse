#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uninstalling Jaeger for Thanos (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/jaeger.yaml" -n thanos --context "${KUBE_CONTEXT}"

echo "==> Done."
