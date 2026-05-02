#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Uninstalling ArgoCD (context: ${KUBE_CONTEXT})"

kubectl delete namespace argocd --context "${KUBE_CONTEXT}"

echo "==> Done."
