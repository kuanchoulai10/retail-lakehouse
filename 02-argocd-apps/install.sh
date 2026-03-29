#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Applying ArgoCD root app (context: ${KUBE_CONTEXT})"

kubectl apply -f root-app.yaml --context "${KUBE_CONTEXT}"

echo "==> Done. ArgoCD will now reconcile all child applications."
