#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Uninstalling Prometheus Operator (context: ${KUBE_CONTEXT})"

kubectl delete -k . --context "${KUBE_CONTEXT}"

echo "==> Done."
