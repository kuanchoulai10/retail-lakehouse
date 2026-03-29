#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

echo "==> Uninstalling Trino (context: ${KUBE_CONTEXT})"

helm uninstall trino \
  --namespace trino \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
