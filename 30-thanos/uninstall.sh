#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Uninstalling Thanos (context: ${KUBE_CONTEXT})"

kubectl delete -f manifests/ --context "${KUBE_CONTEXT}"

echo "==> Done."
