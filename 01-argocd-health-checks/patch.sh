#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Patching ArgoCD configmap (context: ${KUBE_CONTEXT})"

kubectl patch configmap argocd-cm \
  -n argocd \
  --patch-file "$SCRIPT_DIR/argocd-cm-patch.yaml" \
  --context "${KUBE_CONTEXT}"

echo "==> Done."
