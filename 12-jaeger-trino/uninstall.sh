#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Uninstalling Jaeger for Trino (context: ${KUBE_CONTEXT})"

kubectl delete -f jaeger.yaml -n trino --context "${KUBE_CONTEXT}"

echo "==> Done."
