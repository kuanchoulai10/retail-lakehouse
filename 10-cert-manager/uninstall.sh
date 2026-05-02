#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Uninstalling cert-manager (context: ${KUBE_CONTEXT})"

helm uninstall cert-manager \
  --namespace cert-manager \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
