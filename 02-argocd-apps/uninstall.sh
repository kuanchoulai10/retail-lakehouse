#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deleting ArgoCD root app (context: ${KUBE_CONTEXT})"

kubectl delete -f root-app.yaml --context "${KUBE_CONTEXT}"

echo "==> Done."
