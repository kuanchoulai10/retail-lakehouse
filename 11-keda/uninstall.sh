#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

echo "==> Uninstalling KEDA (context: ${KUBE_CONTEXT})"

helm uninstall keda \
  --namespace keda \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
