#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Applying ArgoCD root app (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/root-app.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done. ArgoCD will now reconcile all child applications."
