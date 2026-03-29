#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Uninstalling Jaeger for Trino (context: ${KUBE_CONTEXT})"

kubectl delete -f jaeger.yaml -n trino --context "${KUBE_CONTEXT}"

echo "==> Done."
