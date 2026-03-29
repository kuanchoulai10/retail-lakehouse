#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Applying ArgoCD root app (context: ${KUBE_CONTEXT})"

kubectl apply -f root-app.yaml --context "${KUBE_CONTEXT}"

echo "==> Done. ArgoCD will now reconcile all child applications."
